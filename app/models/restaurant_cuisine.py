from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class RestaurantCuisineModel(db.Model):
    __tablename__ = "restaurant_cuisines"
    __table_args__ = (
        UniqueConstraint(
            "restaurant_id",
            "cuisine_type_id",
            name="uq_restaurant_cuisine_restaurant_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    cuisine_type_id: Mapped[int] = mapped_column(
        ForeignKey("cuisine_types.id"), nullable=False, index=True
    )
