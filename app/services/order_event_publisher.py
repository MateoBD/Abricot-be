"""Order domain events.

Thin wrapper kept for backwards compatibility: order.created is now emitted
through the shared ``publish_domain_event`` helper so every domain event shares
one envelope + topic-resolution path.
"""

import logging
from decimal import Decimal
from typing import Any

from app.services.domain_event_publisher import publish_domain_event

logger = logging.getLogger(__name__)


def _event_total(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _order_event_data(order_payload: dict) -> dict:
    return {
        "orderId": order_payload.get("id"),
        "restaurantId": order_payload.get("restaurantId"),
        "userId": order_payload.get("userId"),
        "status": order_payload.get("status"),
        "total": _event_total(order_payload.get("totalAmount")),
        "currency": "ARS",
    }


def publish_order_created(order_payload: dict) -> None:
    publish_domain_event(
        "order.created",
        user_id=order_payload.get("userId"),
        restaurant_id=order_payload.get("restaurantId"),
        payload=_order_event_data(order_payload),
    )
