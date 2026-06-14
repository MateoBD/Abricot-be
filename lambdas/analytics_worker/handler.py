import json
import logging
from typing import Any

from app.repositories.analytics_repository import AnalyticsRepository
from common.flask_db import backend_app_context

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Domain events this worker reacts to by recomputing a restaurant's day aggregate.
_RECOMPUTE_EVENTS = frozenset(
    {"order.created", "order.status_changed", "reservation.created"}
)


def _parse_json(value: str) -> dict | None:
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _domain_event_from_sqs_record(record: dict) -> dict | None:
    body = _parse_json(record.get("body", ""))
    if not body:
        return None

    message = body.get("Message")
    if isinstance(message, str):
        sns_message = _parse_json(message)
        return sns_message if sns_message else None

    return body


def _process_event(event: dict) -> None:
    event_type = event.get("eventType")
    if event_type not in _RECOMPUTE_EVENTS:
        # Explicitly ignore everything else (e.g. promotion.notify).
        logger.info("analytics_worker_skipped_event event_type=%s", event_type)
        return

    data = event.get("data") if isinstance(event.get("data"), dict) else {}

    with backend_app_context():
        target = AnalyticsRepository.resolve_recompute_target(event_type, data)
        if target is None:
            logger.warning(
                "analytics_worker_skipped_unresolvable event_type=%s order_id=%s reservation_id=%s",
                event_type,
                data.get("orderId"),
                data.get("reservationId"),
            )
            return

        restaurant_id, day = target
        AnalyticsRepository.recompute_day_snapshot(restaurant_id, day)
        logger.info(
            "analytics_worker_recomputed event_type=%s restaurant_id=%s period_date=%s",
            event_type,
            restaurant_id,
            day.isoformat(),
        )


def handler(event: dict[str, Any], context):
    failures = []
    for record in event.get("Records", []):
        message_id = record.get("messageId")
        try:
            domain_event = _domain_event_from_sqs_record(record)
            if not domain_event:
                logger.warning("analytics_worker_skipped_invalid_message message_id=%s", message_id)
                continue
            _process_event(domain_event)
        except Exception:
            logger.exception("analytics_worker_record_failed message_id=%s", message_id)
            if message_id:
                failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": failures}
