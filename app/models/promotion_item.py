from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class PromotionItemModel(db.Model):
    __tablename__ = "promotion_items"
    __table_args__ = (
        UniqueConstraint(
            "promotion_id",
            "menu_item_id",
            name="uq_promotion_item_pair",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    promotion_id: Mapped[int] = mapped_column(
        ForeignKey("promotions.id"), nullable=False, index=True
    )
    menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("menu_items.id"), nullable=False, index=True
    )
