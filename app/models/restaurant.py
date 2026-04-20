from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class RestaurantModel(db.Model):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    neighbourhood_id: Mapped[int | None] = mapped_column(
        ForeignKey("neighbourhoods.id"),
        nullable=True,
        index=True,
    )
    price_range_id: Mapped[int | None] = mapped_column(
        ForeignKey("price_ranges.id"),
        nullable=True,
        index=True,
    )
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    allow_table_joining: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    default_slot_duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=90,
        server_default="90",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "cityId": self.city_id,
            "neighbourhoodId": self.neighbourhood_id,
            "priceRangeId": self.price_range_id,
            "phone": self.phone,
            "email": self.email,
            "description": self.description,
            "photoUrl": self.photo_url,
            "allowTableJoining": self.allow_table_joining,
            "defaultSlotDurationMinutes": self.default_slot_duration_minutes,
            "createdAt": self.created_at.isoformat(),
        }
