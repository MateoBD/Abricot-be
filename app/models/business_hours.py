from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, Time, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.utils.uuid7 import new_uuid7

_DAY_NAMES = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}


class BusinessHoursModel(db.Model):
    __tablename__ = "business_hours"
    __table_args__ = (
        UniqueConstraint(
            "restaurant_id",
            "day_of_week",
            name="uq_business_hours_restaurant_day",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=new_uuid7
    )
    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    opens_at: Mapped[object | None] = mapped_column(Time, nullable=True)
    closes_at: Mapped[object | None] = mapped_column(Time, nullable=True)
    is_closed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "restaurantId": str(self.restaurant_id),
            "dayOfWeek": self.day_of_week,
            "dayName": _DAY_NAMES.get(self.day_of_week, "Desconocido"),
            "opensAt": self.opens_at.isoformat() if self.opens_at else None,
            "closesAt": self.closes_at.isoformat() if self.closes_at else None,
            "isClosed": self.is_closed,
        }
