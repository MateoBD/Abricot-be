import logging
from uuid import UUID

from app.models.notification_event import NotificationEventStatus, NotificationEventType
from app.repositories.notification_event_repository import NotificationEventRepository

logger = logging.getLogger(__name__)

# Global async worker instance (initialized in create_app)
_async_worker = None


def set_async_worker(worker) -> None:
    """Set the global async worker (called by create_app)."""
    global _async_worker
    _async_worker = worker


def get_async_worker():
    """Get the global async worker instance."""
    global _async_worker
    return _async_worker


def _send_email_sync(
    to: str,
    subject: str,
    body: str,
    *,
    event_id: UUID | None = None,
) -> bool:
    """
    Send an email synchronously. Uses MockSES in non-production environments.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body text.
        event_id: Optional notification event ID for audit log update.

    Returns:
        True if successful, False otherwise.
    """
    try:
        from flask import current_app

        use_mock = current_app.config.get("ENV") in ("testing", "development") or (
            not current_app.config.get("AWS_SES_REGION")
        )
    except RuntimeError:
        use_mock = True

    if use_mock:
        logger.info(
            "notification_event_sent",
            extra={
                "recipient": to,
                "subject": subject,
                "method": "mock",
                "event_id": str(event_id) if event_id else None,
            },
        )
        if event_id:
            NotificationEventRepository.mark_sent(event_id)
        return True

    try:
        import boto3

        from flask import current_app

        ses = boto3.client("ses", region_name=current_app.config.get("AWS_SES_REGION"))
        ses.send_email(
            Source=current_app.config.get("FROM_EMAIL", "noreply@abricot.com"),
            Destination={"ToAddresses": [to]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Text": {"Data": body}},
            },
        )
        logger.info(
            "notification_event_sent",
            extra={
                "recipient": to,
                "subject": subject,
                "method": "aws_ses",
                "event_id": str(event_id) if event_id else None,
            },
        )
        if event_id:
            NotificationEventRepository.mark_sent(event_id)
        return True
    except Exception as exc:
        error_msg = str(exc)
        logger.error(
            "notification_event_failed",
            extra={
                "recipient": to,
                "subject": subject,
                "error": error_msg,
                "event_id": str(event_id) if event_id else None,
            },
            exc_info=True,
        )
        if event_id:
            NotificationEventRepository.mark_failed(event_id, error_msg, retry=True)
        return False


def _send_email_async(
    to: str,
    subject: str,
    body: str,
    *,
    event_id: UUID | None = None,
) -> None:
    """
    Queue an email for asynchronous sending via the async worker.

    Falls back to sync send if worker not initialized (e.g., in tests).

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body text.
        event_id: Optional notification event ID for audit log update.
    """
    worker = get_async_worker()
    if worker is None:
        # Fallback: send synchronously
        _send_email_sync(to, subject, body, event_id=event_id)
        return

    worker.enqueue(recipient=to, subject=subject, body=body, event_id=event_id)


class NotificationService:
    """
    Service for sending transactional and marketing notifications.

    All methods create audit log entries in notification_events table.
    Emails are sent asynchronously by default (fallback to sync in testing).
    """

    @staticmethod
    def send_reservation_confirmation(reservation_id: UUID) -> None:
        """
        Send reservation confirmation email to guest or registered user.

        Args:
            reservation_id: UUID of the reservation.
        """
        from app.repositories.reservation_repository import ReservationRepository

        reservation = ReservationRepository.get_by_id(reservation_id)
        if not reservation:
            logger.warning("reservation_confirmation_event_not_found", extra={"reservation_id": str(reservation_id)})
            return

        recipient = reservation.guest_email
        if not recipient and reservation.user_id:
            from app.repositories.user_repository import UserRepository

            user = UserRepository.get_by_id(reservation.user_id)
            recipient = user.email if user else None

        if not recipient:
            logger.warning(
                "reservation_confirmation_no_recipient", extra={"reservation_id": str(reservation_id)}
            )
            return

        subject = f"Reserva confirmada — Código {reservation.confirmation_code}"
        body = (
            f"Tu reserva ha sido confirmada.\n\n"
            f"Código de confirmación: {reservation.confirmation_code}\n"
            f"Fecha: {reservation.date.isoformat()}\n"
            f"Hora: {reservation.time_slot.isoformat()}\n"
            f"Personas: {reservation.party_size}\n"
        )

        event = NotificationEventRepository.log_event(
            event_type=NotificationEventType.RESERVATION_CONFIRMATION,
            recipient_email=recipient,
            subject=subject,
            body=body,
            status=NotificationEventStatus.PENDING,
            user_id=reservation.user_id,
            restaurant_id=reservation.restaurant_id,
            reservation_id=reservation_id,
        )

        logger.info(
            "reservation_confirmation_queued",
            extra={
                "reservation_id": str(reservation_id),
                "event_id": str(event.id),
                "user_id": str(reservation.user_id) if reservation.user_id else None,
            },
        )
        _send_email_async(recipient, subject, body, event_id=event.id)

    @staticmethod
    def send_reservation_cancelled(reservation_id: UUID) -> None:
        """
        Send reservation cancellation email to guest or registered user.

        Args:
            reservation_id: UUID of the cancelled reservation.
        """
        from app.repositories.reservation_repository import ReservationRepository

        reservation = ReservationRepository.get_by_id(reservation_id)
        if not reservation:
            logger.warning("reservation_cancelled_event_not_found", extra={"reservation_id": str(reservation_id)})
            return

        recipient = reservation.guest_email
        if not recipient and reservation.user_id:
            from app.repositories.user_repository import UserRepository

            user = UserRepository.get_by_id(reservation.user_id)
            recipient = user.email if user else None

        if not recipient:
            logger.warning(
                "reservation_cancelled_no_recipient", extra={"reservation_id": str(reservation_id)}
            )
            return

        subject = "Reserva cancelada"
        body = (
            f"Tu reserva (código {reservation.confirmation_code}) ha sido cancelada.\n"
            f"Fecha: {reservation.date.isoformat()}, Hora: {reservation.time_slot.isoformat()}\n"
        )

        event = NotificationEventRepository.log_event(
            event_type=NotificationEventType.RESERVATION_CANCELLED,
            recipient_email=recipient,
            subject=subject,
            body=body,
            status=NotificationEventStatus.PENDING,
            user_id=reservation.user_id,
            restaurant_id=reservation.restaurant_id,
            reservation_id=reservation_id,
        )

        logger.info(
            "reservation_cancelled_queued",
            extra={
                "reservation_id": str(reservation_id),
                "event_id": str(event.id),
            },
        )
        _send_email_async(recipient, subject, body, event_id=event.id)

    @staticmethod
    def send_order_confirmation(order_id: UUID) -> None:
        """
        Send order confirmation email to user.

        Args:
            order_id: UUID of the order.
        """
        from app.repositories.order_repository import OrderRepository
        from app.repositories.user_repository import UserRepository

        order = OrderRepository.get_by_id(order_id)
        if not order:
            logger.warning("order_confirmation_event_not_found", extra={"order_id": str(order_id)})
            return

        user = UserRepository.get_by_id(order.user_id)
        if not user:
            logger.warning(
                "order_confirmation_user_not_found",
                extra={"order_id": str(order_id), "user_id": str(order.user_id)},
            )
            return

        subject = "Pedido recibido"
        body = (
            f"Tu pedido ha sido recibido.\n" f"Total: ${order.total_amount:.2f}\n" f"Estado: {order.status.value}\n"
        )

        event = NotificationEventRepository.log_event(
            event_type=NotificationEventType.ORDER_CONFIRMATION,
            recipient_email=user.email,
            subject=subject,
            body=body,
            status=NotificationEventStatus.PENDING,
            user_id=order.user_id,
            restaurant_id=order.restaurant_id,
            order_id=order_id,
        )

        logger.info(
            "order_confirmation_queued",
            extra={
                "order_id": str(order_id),
                "event_id": str(event.id),
                "user_id": str(order.user_id),
            },
        )
        _send_email_async(user.email, subject, body, event_id=event.id)

    @staticmethod
    def send_order_status_update(order_id: UUID) -> None:
        """
        Send order status update email to user.

        Args:
            order_id: UUID of the order.
        """
        from app.repositories.order_repository import OrderRepository
        from app.repositories.user_repository import UserRepository

        order = OrderRepository.get_by_id(order_id)
        if not order:
            logger.warning("order_status_update_event_not_found", extra={"order_id": str(order_id)})
            return

        user = UserRepository.get_by_id(order.user_id)
        if not user:
            logger.warning(
                "order_status_update_user_not_found",
                extra={"order_id": str(order_id), "user_id": str(order.user_id)},
            )
            return

        subject = f"Estado de tu pedido: {order.status.value}"
        body = f"El estado de tu pedido ha cambiado a: {order.status.value}\n"

        event = NotificationEventRepository.log_event(
            event_type=NotificationEventType.ORDER_STATUS_UPDATE,
            recipient_email=user.email,
            subject=subject,
            body=body,
            status=NotificationEventStatus.PENDING,
            user_id=order.user_id,
            restaurant_id=order.restaurant_id,
            order_id=order_id,
        )

        logger.info(
            "order_status_update_queued",
            extra={
                "order_id": str(order_id),
                "event_id": str(event.id),
                "status": order.status.value,
            },
        )
        _send_email_async(user.email, subject, body, event_id=event.id)

    @staticmethod
    def send_promotion_notification(promotion_id: UUID) -> None:
        """
        Send promotion notification to all subscribed users.

        Queries notification_preferences to find users who opted in to receive promotions.

        Args:
            promotion_id: UUID of the promotion.
        """
        from app.extensions import db

        from app.models.promotion import PromotionModel
        from app.repositories.notification_preference_repository import NotificationPreferenceRepository

        promo = db.session.get(PromotionModel, promotion_id)
        if not promo:
            logger.warning("promotion_notification_event_not_found", extra={"promotion_id": str(promotion_id)})
            return

        emails = NotificationPreferenceRepository.get_subscribed_emails(promo.restaurant_id, "receive_promotions")

        if not emails:
            logger.info("promotion_notification_no_subscribers", extra={"promotion_id": str(promotion_id)})
            return

        subject = f"Promoción: {promo.title}"
        body = (
            f"Nueva promoción disponible: {promo.title}\n"
            f"{promo.description or ''}\n"
            f"Válida del {promo.start_date} al {promo.end_date}\n"
        )

        for email in emails:
            event = NotificationEventRepository.log_event(
                event_type=NotificationEventType.PROMOTION_NOTIFICATION,
                recipient_email=email,
                subject=subject,
                body=body,
                status=NotificationEventStatus.PENDING,
                restaurant_id=promo.restaurant_id,
                promotion_id=promotion_id,
            )
            _send_email_async(email, subject, body, event_id=event.id)

        logger.info(
            "promotion_notification_broadcast_queued",
            extra={"promotion_id": str(promotion_id), "recipient_count": len(emails)},
        )

    @staticmethod
    def _get_subscribed_user_emails(restaurant_id: UUID, preference_field: str) -> list[str]:
        """
        Get list of emails for users subscribed to a specific notification type.

        Args:
            restaurant_id: UUID of the restaurant.
            preference_field: Preference field name (e.g., 'receive_promotions').

        Returns:
            List of email addresses.
        """
        from app.repositories.notification_preference_repository import NotificationPreferenceRepository

        return NotificationPreferenceRepository.get_subscribed_emails(restaurant_id, preference_field)
