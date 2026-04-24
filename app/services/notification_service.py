import logging
from uuid import UUID

logger = logging.getLogger(__name__)


def _send_email(to: str, subject: str, body: str) -> None:
    """Send an email. Uses MockSESClient in non-production environments."""
    try:
        from flask import current_app
        use_mock = current_app.config.get("ENV") in ("testing", "development") or \
                   not current_app.config.get("AWS_SES_REGION")
    except RuntimeError:
        use_mock = True

    if use_mock:
        logger.info("[MockSES] To: %s | Subject: %s", to, subject)
        return

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
    except Exception:
        logger.exception("SES send failed to %s", to)


class NotificationService:
    @staticmethod
    def send_reservation_confirmation(reservation_id: UUID) -> None:
        from app.repositories.reservation_repository import ReservationRepository
        reservation = ReservationRepository.get_by_id(reservation_id)
        if not reservation:
            logger.warning("send_reservation_confirmation: reservation %s not found", reservation_id)
            return

        recipient = reservation.guest_email
        if not recipient and reservation.user_id:
            from app.repositories.user_repository import UserRepository
            user = UserRepository.get_by_id(reservation.user_id)
            recipient = user.email if user else None

        if not recipient:
            return

        subject = f"Reserva confirmada — Código {reservation.confirmation_code}"
        body = (
            f"Tu reserva ha sido confirmada.\n\n"
            f"Código de confirmación: {reservation.confirmation_code}\n"
            f"Fecha: {reservation.date.isoformat()}\n"
            f"Hora: {reservation.time_slot.isoformat()}\n"
            f"Personas: {reservation.party_size}\n"
        )
        _send_email(recipient, subject, body)
        logger.info("Reservation confirmation sent: reservation_id=%s", reservation_id)

    @staticmethod
    def send_reservation_cancelled(reservation_id: UUID) -> None:
        from app.repositories.reservation_repository import ReservationRepository
        reservation = ReservationRepository.get_by_id(reservation_id)
        if not reservation:
            return

        recipient = reservation.guest_email
        if not recipient and reservation.user_id:
            from app.repositories.user_repository import UserRepository
            user = UserRepository.get_by_id(reservation.user_id)
            recipient = user.email if user else None

        if not recipient:
            return

        subject = "Reserva cancelada"
        body = (
            f"Tu reserva (código {reservation.confirmation_code}) ha sido cancelada.\n"
            f"Fecha: {reservation.date.isoformat()}, Hora: {reservation.time_slot.isoformat()}\n"
        )
        _send_email(recipient, subject, body)
        logger.info("Reservation cancellation sent: reservation_id=%s", reservation_id)

    @staticmethod
    def send_order_confirmation(order_id: UUID) -> None:
        from app.repositories.order_repository import OrderRepository
        from app.repositories.user_repository import UserRepository
        order = OrderRepository.get_by_id(order_id)
        if not order:
            return
        user = UserRepository.get_by_id(order.user_id)
        if not user:
            return

        subject = "Pedido recibido"
        body = (
            f"Tu pedido ha sido recibido.\n"
            f"Total: ${order.total_amount:.2f}\n"
            f"Estado: {order.status.value}\n"
        )
        _send_email(user.email, subject, body)
        logger.info("Order confirmation sent: order_id=%s", order_id)

    @staticmethod
    def send_order_status_update(order_id: UUID) -> None:
        from app.repositories.order_repository import OrderRepository
        from app.repositories.user_repository import UserRepository
        order = OrderRepository.get_by_id(order_id)
        if not order:
            return
        user = UserRepository.get_by_id(order.user_id)
        if not user:
            return

        subject = f"Estado de tu pedido: {order.status.value}"
        body = f"El estado de tu pedido ha cambiado a: {order.status.value}\n"
        _send_email(user.email, subject, body)
        logger.info("Order status update sent: order_id=%s status=%s", order_id, order.status)

    @staticmethod
    def send_promotion_notification(promotion_id: UUID) -> None:
        from app.extensions import db
        from app.models.promotion import PromotionModel
        from app.repositories.notification_preference_repository import NotificationPreferenceRepository

        promo = db.session.get(PromotionModel, promotion_id)
        if not promo:
            return

        emails = NotificationPreferenceRepository.get_subscribed_emails(
            promo.restaurant_id, "receive_promotions"
        )
        subject = f"Promoción: {promo.title}"
        body = (
            f"Nueva promoción disponible: {promo.title}\n"
            f"{promo.description or ''}\n"
            f"Válida del {promo.start_date} al {promo.end_date}\n"
        )
        for email in emails:
            _send_email(email, subject, body)
        logger.info(
            "Promotion notification sent: promo_id=%s recipients=%d", promotion_id, len(emails)
        )

    @staticmethod
    def _get_subscribed_user_emails(restaurant_id: UUID, preference_field: str) -> list[str]:
        from app.repositories.notification_preference_repository import NotificationPreferenceRepository
        return NotificationPreferenceRepository.get_subscribed_emails(
            restaurant_id, preference_field
        )
