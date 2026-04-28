"""Repository for notification event auditing."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from app.extensions import db
from app.models.notification_event import NotificationEventModel, NotificationEventStatus, NotificationEventType


class NotificationEventRepository:
    """Repository for notification audit logs."""

    @staticmethod
    def log_event(
        event_type: NotificationEventType,
        recipient_email: str,
        subject: str,
        body: str,
        status: NotificationEventStatus = NotificationEventStatus.PENDING,
        user_id: UUID | None = None,
        restaurant_id: UUID | None = None,
        reservation_id: UUID | None = None,
        order_id: UUID | None = None,
        promotion_id: UUID | None = None,
    ) -> NotificationEventModel:
        """Log a notification event."""
        event = NotificationEventModel(
            event_type=event_type,
            recipient_email=recipient_email,
            subject=subject,
            body=body,
            status=status,
            user_id=user_id,
            restaurant_id=restaurant_id,
            reservation_id=reservation_id,
            order_id=order_id,
            promotion_id=promotion_id,
        )
        db.session.add(event)
        db.session.commit()
        return event

    @staticmethod
    def mark_sent(event_id: UUID) -> NotificationEventModel | None:
        """Mark an event as successfully sent."""
        event = db.session.get(NotificationEventModel, event_id)
        if event:
            event.status = NotificationEventStatus.SENT
            event.sent_at = datetime.utcnow()
            db.session.commit()
        return event

    @staticmethod
    def mark_failed(event_id: UUID, error_message: str, retry: bool = False) -> NotificationEventModel | None:
        """Mark an event as failed with error details."""
        event = db.session.get(NotificationEventModel, event_id)
        if event:
            event.retry_count += 1
            event.error_message = error_message
            event.status = NotificationEventStatus.RETRIED if retry else NotificationEventStatus.FAILED
            db.session.commit()
        return event

    @staticmethod
    def get_by_id(event_id: UUID) -> NotificationEventModel | None:
        """Get an event by ID."""
        return db.session.get(NotificationEventModel, event_id)

    @staticmethod
    def get_by_restaurant(restaurant_id: UUID, limit: int = 100) -> list[NotificationEventModel]:
        """Get all events for a restaurant."""
        return list(
            db.session.execute(
                select(NotificationEventModel)
                .where(NotificationEventModel.restaurant_id == restaurant_id)
                .order_by(NotificationEventModel.created_at.desc())
                .limit(limit)
            ).scalars()
        )

    @staticmethod
    def get_failed_events(limit: int = 100) -> list[NotificationEventModel]:
        """Get all failed events for retry."""
        return list(
            db.session.execute(
                select(NotificationEventModel)
                .where(NotificationEventModel.status == NotificationEventStatus.FAILED)
                .order_by(NotificationEventModel.created_at.asc())
                .limit(limit)
            ).scalars()
        )
