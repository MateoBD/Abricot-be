import importlib
import json
import os
import sys
from contextlib import contextmanager
from datetime import date
from uuid import UUID

import pytest

# The worker module lives under lambdas/analytics_worker and imports
# `common.flask_db`. Both `common` (under lambdas/) and the handler module become
# importable once those directories are on sys.path, exactly like the runtime
# package layout produced by scripts/package_lambdas.sh.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LAMBDAS_DIR = os.path.join(_ROOT, "lambdas")
_WORKER_DIR = os.path.join(_LAMBDAS_DIR, "analytics_worker")
for _path in (_LAMBDAS_DIR, _WORKER_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

handler_module = importlib.import_module("handler")


RESTAURANT_ID = UUID("00000000-0000-0000-0000-000000000010")
ORDER_ID = UUID("00000000-0000-0000-0000-000000000020")
RESERVATION_ID = UUID("00000000-0000-0000-0000-000000000030")
DAY = date(2026, 6, 14)


@contextmanager
def _noop_context():
    yield


@pytest.fixture(autouse=True)
def _patch_app_context(monkeypatch):
    """Replace the Flask/SQLAlchemy app context with a no-op so no DB is needed."""
    monkeypatch.setattr(handler_module, "backend_app_context", _noop_context)


def _sqs_event(domain_event: dict, message_id: str = "m1") -> dict:
    # SQS delivers the SNS envelope; the handler unwraps body -> Message (JSON).
    sns_envelope = {"Message": json.dumps(domain_event)}
    return {
        "Records": [
            {"messageId": message_id, "body": json.dumps(sns_envelope)},
        ]
    }


def test_ignores_promotion_notify(monkeypatch):
    calls = []

    def fake_resolve(event_type, data):
        calls.append((event_type, data))
        return (RESTAURANT_ID, DAY)

    def fake_recompute(restaurant_id, day):
        calls.append(("recompute", restaurant_id, day))
        return {}

    monkeypatch.setattr(
        handler_module.AnalyticsRepository, "resolve_recompute_target", fake_resolve
    )
    monkeypatch.setattr(
        handler_module.AnalyticsRepository, "recompute_day_snapshot", fake_recompute
    )

    event = _sqs_event(
        {
            "eventType": "promotion.notify",
            "restaurantId": str(RESTAURANT_ID),
            "data": {"promotionId": "p1"},
        }
    )
    result = handler_module.handler(event, None)

    assert result == {"batchItemFailures": []}
    assert calls == []  # never touched the repository


@pytest.mark.parametrize(
    ("event_type", "data"),
    [
        ("order.created", {"orderId": str(ORDER_ID)}),
        ("order.status_changed", {"orderId": str(ORDER_ID)}),
        ("reservation.created", {"reservationId": str(RESERVATION_ID)}),
    ],
)
def test_recomputes_for_order_and_reservation_events(monkeypatch, event_type, data):
    resolved = []
    recomputed = []

    def fake_resolve(evt, payload):
        resolved.append((evt, payload))
        return (RESTAURANT_ID, DAY)

    def fake_recompute(restaurant_id, day):
        recomputed.append((restaurant_id, day))
        return {"restaurantId": str(restaurant_id), "periodDate": day.isoformat()}

    monkeypatch.setattr(
        handler_module.AnalyticsRepository, "resolve_recompute_target", fake_resolve
    )
    monkeypatch.setattr(
        handler_module.AnalyticsRepository, "recompute_day_snapshot", fake_recompute
    )

    event = _sqs_event({"eventType": event_type, "data": data})
    result = handler_module.handler(event, None)

    assert result == {"batchItemFailures": []}
    assert resolved == [(event_type, data)]
    assert recomputed == [(RESTAURANT_ID, DAY)]


def test_unresolvable_target_is_skipped_not_failed(monkeypatch):
    recomputed = []

    monkeypatch.setattr(
        handler_module.AnalyticsRepository,
        "resolve_recompute_target",
        lambda evt, payload: None,
    )
    monkeypatch.setattr(
        handler_module.AnalyticsRepository,
        "recompute_day_snapshot",
        lambda restaurant_id, day: recomputed.append((restaurant_id, day)),
    )

    event = _sqs_event({"eventType": "order.created", "data": {}})
    result = handler_module.handler(event, None)

    assert result == {"batchItemFailures": []}
    assert recomputed == []  # skipped gracefully, no recompute, no failure


def test_returns_batch_item_failures_on_error(monkeypatch):
    def boom(evt, payload):
        raise RuntimeError("db exploded")

    monkeypatch.setattr(
        handler_module.AnalyticsRepository, "resolve_recompute_target", boom
    )

    event = _sqs_event(
        {"eventType": "order.created", "data": {"orderId": str(ORDER_ID)}},
        message_id="bad-1",
    )
    result = handler_module.handler(event, None)

    assert result == {"batchItemFailures": [{"itemIdentifier": "bad-1"}]}


def test_invalid_message_is_skipped(monkeypatch):
    monkeypatch.setattr(
        handler_module.AnalyticsRepository,
        "resolve_recompute_target",
        lambda evt, payload: (_ for _ in ()).throw(AssertionError("should not run")),
    )

    event = {"Records": [{"messageId": "x", "body": "not-json"}]}
    result = handler_module.handler(event, None)

    assert result == {"batchItemFailures": []}
