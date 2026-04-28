"""Notification event audit log model."""
from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import DateTime, Enum as EnumColumn, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.utils.uuid7 import new_uuid7


class NotificationEventType(str, Enum):
    """Event types for notification auditing."""

    RESERVATION_CONFIRMATION = "RESERVATION_CONFIRMATION"
    RESERVATION_CANCELLED = "RESERVATION_CANCELLED"
    ORDER_CONFIRMATION = "ORDER_CONFIRMATION"
    ORDER_STATUS_UPDATE = "ORDER_STATUS_UPDATE"
    PROMOTION_NOTIFICATION = "PROMOTION_NOTIFICATION"


class NotificationEventStatus(str, Enum):
    """Status of a notification event."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    RETRIED = "RETRIED"


class NotificationEventModel(db.Model):
    """Audit log for all notification events."""

    __tablename__ = "notification_events"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=new_uuid7
    )
    event_type: Mapped[NotificationEventType] = mapped_column(
        EnumColumn(NotificationEventType), nullable=False, index=True
    )
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[NotificationEventStatus] = mapped_column(
        EnumColumn(NotificationEventStatus), nullable=False, default=NotificationEventStatus.PENDING
    )
    retry_count: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Foreign keys for traceability
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    restaurant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("restaurants.id"), nullable=True, index=True
    )
    reservation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("reservations.id"), nullable=True, index=True
    )
    order_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("orders.id"), nullable=True, index=True
    )
    promotion_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("promotions.id"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "eventType": self.event_type.value,
            "recipientEmail": self.recipient_email,
            "subject": self.subject,
            "body": self.body,
            "status": self.status.value,
            "retryCount": self.retry_count,
            "errorMessage": self.error_message,
            "userId": str(self.user_id) if self.user_id else None,
            "restaurantId": str(self.restaurant_id) if self.restaurant_id else None,
            "reservationId": str(self.reservation_id) if self.reservation_id else None,
            "orderId": str(self.order_id) if self.order_id else None,
            "promotionId": str(self.promotion_id) if self.promotion_id else None,
            "createdAt": self.created_at.isoformat(),
            "sentAt": self.sent_at.isoformat() if self.sent_at else None,
            "updatedAt": self.updated_at.isoformat(),
        }
