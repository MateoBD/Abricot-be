import json
import logging
import os
from datetime import UTC, datetime
from uuid import UUID

from flask import current_app

from app.models.enums import UserSnsSubscriptionStatus
from app.models.user import UserModel
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

_PENDING_ARN = "PendingConfirmation"
# AWS returns these placeholder strings (not real ARNs) for the SubscriptionArn of
# an unconfirmed / removed email subscription. Neither means "confirmed".
_PLACEHOLDER_ARNS = frozenset({_PENDING_ARN, "Deleted"})


def _sns_client():
    import boto3
    from botocore.config import Config

    region = current_app.config.get("AWS_REGION") or None
    endpoint_url = (
        current_app.config.get("LOCALSTACK_ENDPOINT")
        if current_app.config.get("USE_LOCALSTACK")
        else None
    )
    kwargs = {
        "config": Config(
            connect_timeout=1,
            read_timeout=2,
            retries={"max_attempts": 1},
        )
    }
    if region:
        kwargs["region_name"] = region
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
    return boto3.client("sns", **kwargs)


def _shared_topic_arn() -> str | None:
    """ARN of the single shared notification topic (env first, then app config).

    Reading os.environ first means this works in the worker/no-app-context paths
    too. EMAIL_NOTIFICATIONS_TOPIC_ARN is injected by Terraform (infra/locals.tf).
    """
    arn = os.environ.get("EMAIL_NOTIFICATIONS_TOPIC_ARN", "").strip()
    if not arn:
        try:
            arn = (current_app.config.get("EMAIL_NOTIFICATIONS_TOPIC_ARN") or "").strip()
        except RuntimeError:
            arn = ""
    return arn or None


def _is_real_subscription_arn(value: str | None) -> bool:
    return bool(value and value not in _PLACEHOLDER_ARNS and value.startswith("arn:"))


def _user_filter_policy(user_id: UUID | str) -> str:
    """SNS subscription filter policy that targets exactly this user.

    FilterPolicyScope defaults to MessageAttributes, so this matches the
    ``userId`` message attribute set by ``publish_user_notification``.
    """
    return json.dumps({"userId": [str(user_id)]})


def publish_user_notification(user_id: UUID | str, subject: str, message: str) -> str | None:
    """THE single publish path for user emails.

    Always publishes to the shared topic and ALWAYS sets the ``userId`` message
    attribute, so the recipient's filter policy matches. A filter policy silently
    drops a message whose attribute is missing/wrong, hence "always set userId"
    is a hard invariant here. Returns the SNS MessageId (or None if no topic).
    """
    topic_arn = _shared_topic_arn()
    if not topic_arn:
        logger.error(
            "user_notification_publish_skipped_missing_topic user_id=%s", user_id
        )
        return None
    response = _sns_client().publish(
        TopicArn=topic_arn,
        Subject=(subject or "")[:100],
        Message=message,
        MessageAttributes={
            "userId": {"DataType": "String", "StringValue": str(user_id)}
        },
    )
    message_id = response.get("MessageId")
    logger.info(
        "user_notification_published user_id=%s message_id=%s", user_id, message_id
    )
    return message_id


class SnsUserNotificationService:
    @staticmethod
    def ensure_subscription(user: UserModel) -> UserModel:
        """Subscribe the user's email to the shared topic with a userId filter.

        Best-effort: never raises into signup; records FAILED + logs on error.
        """
        if user.sns_topic_arn and user.sns_subscription_status in (
            UserSnsSubscriptionStatus.PENDING_CONFIRMATION,
            UserSnsSubscriptionStatus.CONFIRMED,
        ):
            return user

        requested_at = datetime.now(UTC)
        topic_arn = _shared_topic_arn()
        if not topic_arn:
            logger.error(
                "user_sns_subscription_missing_topic user_id=%s", str(user.id)
            )
            return UserRepository.update_sns_subscription(
                user,
                topic_arn=user.sns_topic_arn,
                subscription_arn=user.sns_subscription_arn,
                status=UserSnsSubscriptionStatus.FAILED,
                requested_at=requested_at,
            )

        try:
            sns = _sns_client()
            subscription = sns.subscribe(
                TopicArn=topic_arn,
                Protocol="email",
                Endpoint=user.email,
                Attributes={"FilterPolicy": _user_filter_policy(user.id)},
                ReturnSubscriptionArn=True,
            )
            subscription_arn = subscription.get("SubscriptionArn") or _PENDING_ARN
            status = (
                UserSnsSubscriptionStatus.CONFIRMED
                if _is_real_subscription_arn(subscription_arn)
                else UserSnsSubscriptionStatus.PENDING_CONFIRMATION
            )
            return UserRepository.update_sns_subscription(
                user,
                topic_arn=topic_arn,
                subscription_arn=subscription_arn,
                status=status,
                requested_at=requested_at,
            )
        except Exception:
            logger.exception(
                "user_sns_subscription_request_failed",
                extra={"user_id": str(user.id), "email": user.email},
            )
            return UserRepository.update_sns_subscription(
                user,
                topic_arn=user.sns_topic_arn,
                subscription_arn=user.sns_subscription_arn,
                status=UserSnsSubscriptionStatus.FAILED,
                requested_at=requested_at,
            )

    @staticmethod
    def refresh_subscription_status(user: UserModel) -> UserModel:
        topic_arn = _shared_topic_arn() or user.sns_topic_arn
        if not topic_arn or not user.sns_topic_arn:
            return SnsUserNotificationService.ensure_subscription(user)

        try:
            # All users share ONE topic, so this lists every user's subscription.
            # Match on this user's email endpoint and prefer a CONFIRMED (real-ARN)
            # subscription; AWS often leaves stale "PendingConfirmation"/"Deleted"
            # duplicate rows alongside the confirmed one.
            confirmed_arn: str | None = None
            paginator = _sns_client().get_paginator("list_subscriptions_by_topic")
            for page in paginator.paginate(TopicArn=topic_arn):
                for subscription in page.get("Subscriptions", []):
                    if str(subscription.get("Protocol", "")).lower() != "email":
                        continue
                    if str(subscription.get("Endpoint", "")).lower() != user.email.lower():
                        continue
                    arn = subscription.get("SubscriptionArn") or _PENDING_ARN
                    if _is_real_subscription_arn(arn):
                        confirmed_arn = arn
                        break
                if confirmed_arn:
                    break

            status = (
                UserSnsSubscriptionStatus.CONFIRMED
                if confirmed_arn
                else UserSnsSubscriptionStatus.PENDING_CONFIRMATION
            )
            return UserRepository.update_sns_subscription(
                user,
                topic_arn=topic_arn,
                subscription_arn=confirmed_arn or user.sns_subscription_arn,
                status=status,
                requested_at=user.sns_subscription_requested_at,
            )
        except Exception:
            logger.exception(
                "user_sns_subscription_refresh_failed",
                extra={"user_id": str(user.id), "topic_arn": topic_arn},
            )
            return UserRepository.update_sns_subscription(
                user,
                topic_arn=user.sns_topic_arn,
                subscription_arn=user.sns_subscription_arn,
                status=UserSnsSubscriptionStatus.FAILED,
                requested_at=user.sns_subscription_requested_at,
            )

    @staticmethod
    def publish_reservation_confirmation(reservation_id: UUID) -> None:
        reservation = ReservationRepository.get_by_id(reservation_id)
        if not reservation or not reservation.user_id:
            return

        user = UserRepository.get_by_id(reservation.user_id)
        # Guard: filter policies drop silently if the recipient has no confirmed
        # subscription, so verify CONFIRMED before publishing and log if not.
        if (
            not user
            or user.sns_subscription_status != UserSnsSubscriptionStatus.CONFIRMED
        ):
            logger.warning(
                "reservation_sns_confirmation_skipped",
                extra={
                    "reservation_id": str(reservation_id),
                    "user_id": str(reservation.user_id),
                    "reason": "subscription_not_confirmed",
                },
            )
            return

        restaurant = RestaurantRepository.get_by_id(reservation.restaurant_id)
        restaurant_name = restaurant.name if restaurant else str(reservation.restaurant_id)
        subject = f"Reserva confirmada - Codigo {reservation.confirmation_code}"
        message = (
            "Tu reserva ha sido confirmada.\n\n"
            f"Codigo de confirmacion: {reservation.confirmation_code}\n"
            f"Restaurante: {restaurant_name}\n"
            f"Fecha: {reservation.date.isoformat()}\n"
            f"Hora: {reservation.time_slot.isoformat()}\n"
            f"Personas: {reservation.party_size}\n"
        )
        publish_user_notification(user.id, subject, message)
        logger.info(
            "reservation_sns_confirmation_published",
            extra={
                "reservation_id": str(reservation_id),
                "user_id": str(user.id),
            },
        )
