from sqlalchemy import Boolean, ForeignKey, Integer, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class BusinessHoursModel(db.Model):
    __tablename__ = "business_hours"
    __table_args__ = (
        UniqueConstraint(
            "restaurant_id",
            "day_of_week",
            name="uq_business_hours_restaurant_day",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
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
