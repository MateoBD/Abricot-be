from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.enums import DiscountType
from app.utils.uuid7 import new_uuid7


class PromotionModel(db.Model):
    __tablename__ = "promotions"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=new_uuid7
    )
    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    discount_type: Mapped[DiscountType] = mapped_column(
        Enum(DiscountType, native_enum=False, validate_strings=True, length=32),
        nullable=False,
    )
    discount_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    notify_users: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "restaurantId": str(self.restaurant_id),
            "title": self.title,
            "description": self.description,
            "discountType": self.discount_type.value,
            "discountValue": f"{self.discount_value:.2f}",
            "startDate": self.start_date.isoformat(),
            "endDate": self.end_date.isoformat(),
            "isActive": self.is_active,
            "notifyUsers": self.notify_users,
            "createdAt": self.created_at.isoformat(),
        }
