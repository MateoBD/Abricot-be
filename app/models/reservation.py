from datetime import UTC, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.enums import ReservationSource, ReservationStatus


class ReservationModel(db.Model):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
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
    confirmation_code: Mapped[str] = mapped_column(String(12), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
