from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.enums import ReservationSource, ReservationStatus
from app.utils.uuid7 import new_uuid7


class ReservationModel(db.Model):
    __tablename__ = "reservations"
    __table_args__ = (
        Index(
            "ix_reservations_restaurant_id_date_status",
            "restaurant_id",
            "date",
            "status",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=new_uuid7
    )
    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    guest_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    guest_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    guest_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[ReservationSource] = mapped_column(
        Enum(ReservationSource, native_enum=False, validate_strings=True, length=16),
        nullable=False,
        default=ReservationSource.ONLINE,
        server_default=ReservationSource.ONLINE.value,
    )
    party_size: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[object] = mapped_column(Date, nullable=False, index=True)
    time_slot: Mapped[object] = mapped_column(Time, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, native_enum=False, validate_strings=True, length=16),
        nullable=False,
        default=ReservationStatus.CONFIRMED,
        server_default=ReservationStatus.CONFIRMED.value,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmation_code: Mapped[str] = mapped_column(
        String(12), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "restaurantId": str(self.restaurant_id),
            "userId": str(self.user_id) if self.user_id else None,
            "guestName": self.guest_name,
            "guestPhone": self.guest_phone,
            "guestEmail": self.guest_email,
            "source": self.source.value,
            "partySize": self.party_size,
            "date": self.date.isoformat(),
            "timeSlot": self.time_slot.isoformat(),
            "status": self.status.value,
            "notes": self.notes,
            "confirmationCode": self.confirmation_code,
            "createdAt": self.created_at.isoformat(),
        }
