from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.utils.uuid7 import new_uuid7


class NotificationPreferenceModel(db.Model):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "restaurant_id",
            name="uq_notification_pref_user_restaurant",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=new_uuid7
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    receive_promotions: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    receive_order_updates: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    receive_reservation_reminders: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "userId": str(self.user_id),
            "restaurantId": str(self.restaurant_id),
            "receivePromotions": self.receive_promotions,
            "receiveOrderUpdates": self.receive_order_updates,
            "receiveReservationReminders": self.receive_reservation_reminders,
        }
