import json
import logging
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
    if event_type != "order.created":
        logger.info("analytics_worker_skipped_unknown_event event_type=%s", event_type)
        return

    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    logger.info(
        "analytics_worker_processed_order_created order_id=%s restaurant_id=%s total=%s status=%s",
        data.get("orderId"),
        data.get("restaurantId"),
        data.get("total"),
        data.get("status"),
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
