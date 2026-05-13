from datetime import time
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.utils.uuid7 import new_uuid7

_DAY_NAMES = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}


class BusinessHoursModel(db.Model):
    """One row = one time range for a given (restaurant, day_of_week).

    Multiple rows with the same (restaurant_id, day_of_week) represent multiple
    opening windows on that day (e.g. lunch + dinner).  A day with no rows is
    considered closed.  Rows are ordered within a day by `sort_order`.
    """

    __tablename__ = "business_hours"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid7)
    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    opens_at: Mapped[time] = mapped_column(Time, nullable=False)
    closes_at: Mapped[time] = mapped_column(Time, nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "restaurantId": str(self.restaurant_id),
            "dayOfWeek": self.day_of_week,
            "opensAt": self.opens_at.isoformat(),
            "closesAt": self.closes_at.isoformat(),
            "sortOrder": self.sort_order,
        }
