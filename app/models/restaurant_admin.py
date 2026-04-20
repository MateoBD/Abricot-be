from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class RestaurantAdminModel(db.Model):
    __tablename__ = "restaurant_admins"
    __table_args__ = (
        UniqueConstraint("user_id", "restaurant_id", name="uq_restaurant_admin_user_restaurant"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
