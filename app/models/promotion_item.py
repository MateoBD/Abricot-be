from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.utils.uuid7 import new_uuid7


class PromotionItemModel(db.Model):
    __tablename__ = "promotion_items"
    __table_args__ = (
        UniqueConstraint(
            "promotion_id",
            "menu_item_id",
            name="uq_promotion_item_pair",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=new_uuid7
    )
    promotion_id: Mapped[UUID] = mapped_column(
        ForeignKey("promotions.id"), nullable=False, index=True
    )
    menu_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("menu_items.id"), nullable=False, index=True
    )
