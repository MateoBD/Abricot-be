import json
import logging
import os
from typing import Any

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_SNS_CLIENT = None


def _sns_client():
    global _SNS_CLIENT
    if _SNS_CLIENT is None:
        _SNS_CLIENT = boto3.client("sns")
    return _SNS_CLIENT


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


def _format_order_created_message(event: dict) -> tuple[str, str]:
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    subject = "Nuevo pedido recibido"
    lines = [
        "Se recibio un nuevo pedido en Abricot.",
        "",
        f"Order ID: {data.get('orderId') or '-'}",
        f"Restaurant ID: {data.get('restaurantId') or '-'}",
        f"User ID: {data.get('userId') or '-'}",
        f"Status: {data.get('status') or '-'}",
        f"Total: {data.get('total') if data.get('total') is not None else '-'} {data.get('currency') or 'ARS'}",
        f"Occurred at: {event.get('occurredAt') or '-'}",
    ]
    return subject, "\n".join(lines)


def _process_event(event: dict) -> None:
    event_type = event.get("eventType")
    if event_type != "order.created":
        logger.info("email_worker_skipped_unknown_event event_type=%s", event_type)
        return

    topic_arn = os.environ.get("EMAIL_TOPIC_ARN", "").strip()
    if not topic_arn:
        raise RuntimeError("missing_EMAIL_TOPIC_ARN")

    subject, message = _format_order_created_message(event)
    order_id = (event.get("data") or {}).get("orderId")
    logger.info("email_worker_publish_attempt order_id=%s", order_id)
    response = _sns_client().publish(
        TopicArn=topic_arn,
        Subject=subject,
        Message=message,
    )
    logger.info(
        "email_worker_publish_succeeded order_id=%s message_id=%s",
        order_id,
        response.get("MessageId"),
    )


def handler(event: dict[str, Any], context):
    failures = []
    for record in event.get("Records", []):
        message_id = record.get("messageId")
        try:
            domain_event = _domain_event_from_sqs_record(record)
            if not domain_event:
                logger.warning("email_worker_skipped_invalid_message message_id=%s", message_id)
                continue
            _process_event(domain_event)
        except Exception:
            logger.exception("email_worker_record_failed message_id=%s", message_id)
            if message_id:
                failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": failures}
