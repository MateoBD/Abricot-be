import json
import logging
import os
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import boto3

logger = logging.getLogger(__name__)

_SNS_CLIENT = None


def _sns_client():
    global _SNS_CLIENT
    if _SNS_CLIENT is None:
        _SNS_CLIENT = boto3.client("sns")
    return _SNS_CLIENT


def _event_total(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _order_created_event(order_payload: dict) -> dict:
    return {
        "eventType": "order.created",
        "eventVersion": "1.0",
        "occurredAt": datetime.now(UTC).isoformat(),
        "source": "orders-service",
        "data": {
            "orderId": order_payload.get("id"),
            "restaurantId": order_payload.get("restaurantId"),
            "userId": order_payload.get("userId"),
            "status": order_payload.get("status"),
            "total": _event_total(order_payload.get("totalAmount")),
            "currency": "ARS",
        },
    }


def publish_order_created(order_payload: dict) -> None:
    topic_arn = os.environ.get("DOMAIN_EVENTS_TOPIC_ARN", "").strip()
    order_id = order_payload.get("id")

    if not topic_arn:
        logger.warning("order_created_publish_skipped_missing_topic order_id=%s", order_id)
        return

    event = _order_created_event(order_payload)
    logger.info("order_created_publish_attempt order_id=%s topic=%s", order_id, topic_arn)
    try:
        response = _sns_client().publish(
            TopicArn=topic_arn,
            Message=json.dumps(event, separators=(",", ":")),
            Subject="order.created",
            MessageAttributes={
                "eventType": {
                    "DataType": "String",
                    "StringValue": "order.created",
                }
            },
        )
        logger.info(
            "order_created_publish_succeeded order_id=%s message_id=%s",
            order_id,
            response.get("MessageId"),
        )
    except Exception:
        logger.exception("order_created_publish_failed order_id=%s", order_id)
