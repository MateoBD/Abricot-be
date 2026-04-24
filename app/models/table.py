from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.utils.uuid7 import new_uuid7


class TableModel(db.Model):
    __tablename__ = "tables"
    __table_args__ = (
        UniqueConstraint("restaurant_id", "number", name="uq_table_restaurant_number"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=new_uuid7
    )
    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_joinable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "restaurantId": str(self.restaurant_id),
            "number": self.number,
            "capacity": self.capacity,
            "name": self.name,
            "isJoinable": self.is_joinable,
            "isActive": self.is_active,
        }
