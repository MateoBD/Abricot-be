"""Single entrypoint for emitting domain events to the domain_events SNS topic.

All backend services publish through ``publish_domain_event``. The topic fans out
(via infra SNS->SQS subscriptions) to the email_events and analytics_events queues;
each worker filters by ``eventType`` per the event contract.

Per-user email delivery: customers receive emails on their per-user SNS topic
(created/subscribed by ``sns_user_notification_service``). Because the worker
Lambdas are packaged WITHOUT the app/DB layer, the recipient topic is resolved
here (publish side, where DB + app context exist) and embedded in the event as
``userTopicArn``; the email worker simply publishes to it.
"""

import json
import logging
import os
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import boto3

logger = logging.getLogger(__name__)

_SNS_CLIENT = None


def _sns_client():
    global _SNS_CLIENT
    if _SNS_CLIENT is None:
        _SNS_CLIENT = boto3.client("sns")
    return _SNS_CLIENT


def _json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def _coerce_uuid(value) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return None


def _resolve_user_topic_arn(user_id) -> str | None:
    """Best-effort lookup of the recipient's confirmed per-user SNS topic ARN.

    Returns None (and never raises) when the user is unknown, has no topic, or
    has not confirmed their email subscription — in which case no email is sent.
    """
    user_uuid = _coerce_uuid(user_id)
    if user_uuid is None:
        return None
    try:
        from app.models.enums import UserSnsSubscriptionStatus
        from app.repositories.user_repository import UserRepository

        user = UserRepository.get_by_id(user_uuid)
        if not user or not user.sns_topic_arn:
            return None
        if user.sns_subscription_status != UserSnsSubscriptionStatus.CONFIRMED:
            return None
        return user.sns_topic_arn
    except Exception:
        logger.exception("domain_event_resolve_user_topic_failed user_id=%s", user_id)
        return None


def publish_domain_event(
    event_type: str,
    user_id=None,
    restaurant_id=None,
    payload: dict | None = None,
) -> None:
    """Publish a domain event to the domain_events SNS topic (best-effort).

    Never raises into the caller: a messaging failure must not break the
    originating business transaction (order create, status change, promo, etc.).
    """
    topic_arn = os.environ.get("DOMAIN_EVENTS_TOPIC_ARN", "").strip()
    if not topic_arn:
        logger.warning(
            "domain_event_publish_skipped_missing_topic event_type=%s", event_type
        )
        return

    event = {
        "eventType": event_type,
        "eventVersion": "1.0",
        "occurredAt": datetime.now(UTC).isoformat(),
        "source": "backend",
        "userId": str(user_id) if user_id is not None else None,
        "restaurantId": str(restaurant_id) if restaurant_id is not None else None,
        "userTopicArn": _resolve_user_topic_arn(user_id),
        "data": payload or {},
    }

    try:
        response = _sns_client().publish(
            TopicArn=topic_arn,
            Message=json.dumps(event, separators=(",", ":"), default=_json_default),
            Subject=event_type[:100],
            MessageAttributes={
                "eventType": {"DataType": "String", "StringValue": event_type}
            },
        )
        logger.info(
            "domain_event_published event_type=%s message_id=%s",
            event_type,
            response.get("MessageId"),
        )
    except Exception:
        logger.exception("domain_event_publish_failed event_type=%s", event_type)
