import json
import logging
from typing import Any

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Event types this worker turns into customer emails. reservation.created is
# intentionally excluded: the reservation flow emails synchronously via the
# user's per-user SNS topic (see sns_user_notification_service).
_HANDLED_EVENT_TYPES = {"order.created", "order.status_changed", "promotion.notify"}

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


def _fmt(value: Any, fallback: str = "-") -> str:
    return str(value) if value not in (None, "") else fallback


def _format_message(event_type: str, data: dict) -> tuple[str, str]:
    if event_type == "order.created":
        subject = "Pedido recibido"
        body = "\n".join(
            [
                "Recibimos tu pedido en Abricot.",
                "",
                f"Pedido: {_fmt(data.get('orderId'))}",
                f"Estado: {_fmt(data.get('status'))}",
                f"Total: {_fmt(data.get('total'))} {_fmt(data.get('currency'), 'ARS')}",
            ]
        )
        return subject, body

    if event_type == "order.status_changed":
        subject = "Estado de tu pedido actualizado"
        body = "\n".join(
            [
                "El estado de tu pedido cambio.",
                "",
                f"Pedido: {_fmt(data.get('orderId'))}",
                f"Nuevo estado: {_fmt(data.get('status'))}",
                f"Estado anterior: {_fmt(data.get('previousStatus'))}",
            ]
        )
        return subject, body

    # promotion.notify
    subject = "Nueva promocion en Abricot"
    body = "\n".join(
        [
            _fmt(data.get("title"), "Tenemos una nueva promocion para vos."),
            "",
            _fmt(data.get("description"), ""),
        ]
    ).rstrip()
    return subject, body


def _process_event(event: dict) -> None:
    event_type = event.get("eventType")
    if event_type not in _HANDLED_EVENT_TYPES:
        logger.info("email_worker_skipped_event event_type=%s", event_type)
        return

    user_topic_arn = (event.get("userTopicArn") or "").strip()
    if not user_topic_arn:
        # No confirmed per-user topic for this recipient -> nothing to deliver.
        logger.info(
            "email_worker_skipped_no_user_topic event_type=%s user_id=%s",
            event_type,
            event.get("userId"),
        )
        return

    subject, message = _format_message(event_type, event.get("data") or {})
    response = _sns_client().publish(
        TopicArn=user_topic_arn,
        Subject=subject[:100],
        Message=message,
    )
    logger.info(
        "email_worker_publish_succeeded event_type=%s message_id=%s",
        event_type,
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
