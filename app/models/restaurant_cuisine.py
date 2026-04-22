from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.utils.uuid7 import new_uuid7


class RestaurantCuisineModel(db.Model):
    __tablename__ = "restaurant_cuisines"
    __table_args__ = (
        UniqueConstraint(
            "restaurant_id",
            "cuisine_type_id",
            name="uq_restaurant_cuisine_restaurant_type",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=new_uuid7
    )
    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    cuisine_type_id: Mapped[UUID] = mapped_column(
        ForeignKey("cuisine_types.id"), nullable=False, index=True
    )
