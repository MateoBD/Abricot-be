from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.utils.uuid7 import new_uuid7


class OrderItemModel(db.Model):
    __tablename__ = "order_items"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=new_uuid7
    )
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    # menu_item_id is kept for traceability/linking even if the item is later
    # renamed or deleted; item_name + unit_price below are the immutable snapshot
    # of what was actually bought and charged.
    menu_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("menu_items.id"), nullable=False, index=True
    )
    item_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    # unit_price is the EFFECTIVE price charged (after active promos). base_unit_price
    # records the pre-discount price and applied_promotion_id the promo that won, so
    # the line is a self-contained record of the discount applied at order time.
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    base_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    # No FK: this is a snapshot id and must survive the promotion being deleted.
    applied_promotion_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "orderId": str(self.order_id),
            "menuItemId": str(self.menu_item_id),
            "itemName": self.item_name,
            "quantity": self.quantity,
            "unitPrice": f"{self.unit_price:.2f}",
            "basePrice": f"{self.base_unit_price:.2f}" if self.base_unit_price is not None else None,
            "appliedPromotionId": str(self.applied_promotion_id)
            if self.applied_promotion_id
            else None,
            "notes": self.notes,
        }
