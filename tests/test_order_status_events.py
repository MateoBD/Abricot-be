from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

import app.services.order_service as order_service_module
from app.exceptions.errors import ConflictError
from app.models.enums import OrderStatus
from app.models.order import OrderModel
from app.services.order_service import OrderService


ORDER_ID = UUID("00000000-0000-0000-0000-000000000001")
RESTAURANT_ID = UUID("00000000-0000-0000-0000-000000000002")
USER_ID = UUID("00000000-0000-0000-0000-000000000003")


def _order(status: OrderStatus) -> OrderModel:
    return OrderModel(
        id=ORDER_ID,
        restaurant_id=RESTAURANT_ID,
        user_id=USER_ID,
        status=status,
        total_amount=Decimal("100.00"),
        created_at=datetime.now(UTC),
    )


def _patch_repository(monkeypatch, order: OrderModel) -> None:
    monkeypatch.setattr(
        order_service_module.OrderRepository,
        "get_by_id",
        lambda order_id: order,
    )

    def update_status(target, new_status, estimated_ready_at=None):
        target.status = new_status
        return target

    monkeypatch.setattr(
        order_service_module.OrderRepository,
        "update_status",
        update_status,
    )
    # _order_payload only reads order items when include_items is True; the
    # cognito path passes restaurant_id, so stub the item lookup to avoid DB.
    monkeypatch.setattr(
        order_service_module.OrderItemRepository,
        "get_by_order",
        lambda order_id: [],
    )


def _capture_events(monkeypatch) -> list[dict]:
    events: list[dict] = []

    def fake_publish(event_type, user_id=None, restaurant_id=None, payload=None):
        events.append(
            {
                "event_type": event_type,
                "user_id": user_id,
                "restaurant_id": restaurant_id,
                "payload": payload,
            }
        )

    monkeypatch.setattr(order_service_module, "publish_domain_event", fake_publish)
    return events


def test_valid_transition_publishes_order_status_changed(monkeypatch):
    order = _order(OrderStatus.PENDING)
    _patch_repository(monkeypatch, order)
    events = _capture_events(monkeypatch)

    OrderService.update_status(
        order_id=ORDER_ID,
        new_status_str="CONFIRMED",
        restaurant_id=RESTAURANT_ID,
    )

    assert len(events) == 1
    event = events[0]
    assert event["event_type"] == "order.status_changed"
    assert event["user_id"] == USER_ID
    assert event["restaurant_id"] == RESTAURANT_ID

    payload = event["payload"]
    assert payload["orderId"] == str(ORDER_ID)
    assert payload["restaurantId"] == str(RESTAURANT_ID)
    assert payload["userId"] == str(USER_ID)
    assert payload["status"] == "CONFIRMED"
    assert payload["previousStatus"] == "PENDING"


def test_invalid_transition_does_not_publish(monkeypatch):
    order = _order(OrderStatus.PENDING)
    _patch_repository(monkeypatch, order)
    events = _capture_events(monkeypatch)

    with pytest.raises(ConflictError):
        OrderService.update_status(
            order_id=ORDER_ID,
            new_status_str="COMPLETED",
            restaurant_id=RESTAURANT_ID,
        )

    assert events == []
