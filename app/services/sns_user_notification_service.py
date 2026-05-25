import logging
import re
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
_TOPIC_SAFE_CHARS = re.compile(r"[^A-Za-z0-9_-]+")


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


def _topic_prefix() -> str:
    return str(current_app.config.get("SNS_USER_TOPIC_PREFIX") or "abricot-user")


def _topic_name(user_id: UUID) -> str:
    prefix = _TOPIC_SAFE_CHARS.sub("-", _topic_prefix()).strip("-_") or "abricot-user"
    return f"{prefix}-{user_id}-notifications"[:256]


def _is_real_subscription_arn(value: str | None) -> bool:
    return bool(value and value != _PENDING_ARN and value.startswith("arn:"))


class SnsUserNotificationService:
    @staticmethod
    def ensure_subscription(user: UserModel) -> UserModel:
        if user.sns_topic_arn and user.sns_subscription_status in (
            UserSnsSubscriptionStatus.PENDING_CONFIRMATION,
            UserSnsSubscriptionStatus.CONFIRMED,
        ):
            return user

        requested_at = datetime.now(UTC)
        try:
            sns = _sns_client()
            topic = sns.create_topic(Name=_topic_name(user.id))
            topic_arn = topic["TopicArn"]
            subscription = sns.subscribe(
                TopicArn=topic_arn,
                Protocol="email",
                Endpoint=user.email,
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
        if not user.sns_topic_arn:
            return SnsUserNotificationService.ensure_subscription(user)

        try:
            paginator = _sns_client().get_paginator("list_subscriptions_by_topic")
            for page in paginator.paginate(TopicArn=user.sns_topic_arn):
                for subscription in page.get("Subscriptions", []):
                    if str(subscription.get("Protocol", "")).lower() != "email":
                        continue
                    if str(subscription.get("Endpoint", "")).lower() != user.email.lower():
                        continue

                    subscription_arn = subscription.get("SubscriptionArn") or _PENDING_ARN
                    status = (
                        UserSnsSubscriptionStatus.CONFIRMED
                        if _is_real_subscription_arn(subscription_arn)
                        else UserSnsSubscriptionStatus.PENDING_CONFIRMATION
                    )
                    return UserRepository.update_sns_subscription(
                        user,
                        topic_arn=user.sns_topic_arn,
                        subscription_arn=subscription_arn,
                        status=status,
                        requested_at=user.sns_subscription_requested_at,
                    )

            return UserRepository.update_sns_subscription(
                user,
                topic_arn=user.sns_topic_arn,
                subscription_arn=user.sns_subscription_arn,
                status=UserSnsSubscriptionStatus.PENDING_CONFIRMATION,
                requested_at=user.sns_subscription_requested_at,
            )
        except Exception:
            logger.exception(
                "user_sns_subscription_refresh_failed",
                extra={"user_id": str(user.id), "topic_arn": user.sns_topic_arn},
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
        if (
            not user
            or user.sns_subscription_status != UserSnsSubscriptionStatus.CONFIRMED
            or not user.sns_topic_arn
        ):
            logger.warning(
                "reservation_sns_confirmation_skipped",
                extra={"reservation_id": str(reservation_id)},
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
        _sns_client().publish(
            TopicArn=user.sns_topic_arn,
            Subject=subject[:100],
            Message=message,
        )
        logger.info(
            "reservation_sns_confirmation_published",
            extra={
                "reservation_id": str(reservation_id),
                "user_id": str(user.id),
                "topic_arn": user.sns_topic_arn,
            },
        )
