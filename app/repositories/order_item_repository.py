from uuid import UUID

from sqlalchemy import select

from app.extensions import db
from app.models.order_item import OrderItemModel


class OrderItemRepository:
    @staticmethod
    def get_by_order(order_id: UUID) -> list[OrderItemModel]:
        return list(
            db.session.execute(
                select(OrderItemModel).where(OrderItemModel.order_id == order_id)
            ).scalars()
        )

    @staticmethod
    def bulk_insert(order_id: UUID, items: list[dict]) -> list[OrderItemModel]:
        """
        Each item: menu_item_id, quantity, unit_price, notes (optional).
        """
        out: list[OrderItemModel] = []
        for row in items:
            oi = OrderItemModel(
                order_id=order_id,
                menu_item_id=row["menu_item_id"],
                quantity=row["quantity"],
                unit_price=row["unit_price"],
                notes=row.get("notes"),
            )
            db.session.add(oi)
            out.append(oi)
        db.session.commit()
        return out
