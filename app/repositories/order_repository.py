from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select

from app.extensions import db
from app.models.enums import OrderStatus
from app.models.order_item import OrderItemModel
from app.models.order import OrderModel


class OrderRepository:
    @staticmethod
    def create(order: OrderModel) -> OrderModel:
        db.session.add(order)
        db.session.commit()
        return order

    @staticmethod
    def create_with_items(order: OrderModel, items: list[dict]) -> tuple[OrderModel, list[OrderItemModel]]:
        db.session.add(order)
        db.session.flush()

        order_items: list[OrderItemModel] = []
        for row in items:
            order_item = OrderItemModel(
                order_id=order.id,
                menu_item_id=row["menu_item_id"],
                quantity=row["quantity"],
                unit_price=row["unit_price"],
                notes=row.get("notes"),
            )
            db.session.add(order_item)
            order_items.append(order_item)

        db.session.commit()
        return order, order_items

    @staticmethod
    def get_by_id(order_id: UUID) -> OrderModel | None:
        return db.session.get(OrderModel, order_id)

    @staticmethod
    def update_status(
        order: OrderModel,
        new_status: OrderStatus,
        estimated_ready_at: datetime | None = None,
    ) -> OrderModel:
        order.status = new_status
        if estimated_ready_at is not None:
            order.estimated_ready_at = estimated_ready_at
        db.session.commit()
        return order

    @staticmethod
    def list_for_restaurant(
        restaurant_id: UUID,
        filters: dict | None,
        page: int,
        per_page: int,
    ) -> tuple[list[OrderModel], int]:
        stmt = select(OrderModel).where(OrderModel.restaurant_id == restaurant_id)
        count_q = select(func.count()).select_from(OrderModel).where(
            OrderModel.restaurant_id == restaurant_id
        )
        if filters and filters.get("status") is not None:
            stmt = stmt.where(OrderModel.status == filters["status"])
            count_q = count_q.where(OrderModel.status == filters["status"])
        total = int(db.session.scalar(count_q) or 0)

        page = max(page, 1)
        per_page = max(min(per_page, 100), 1)
        offset = (page - 1) * per_page

        rows = list(
            db.session.execute(
                stmt.order_by(OrderModel.created_at.desc()).offset(offset).limit(per_page)
            ).scalars()
        )
        return rows, total

    @staticmethod
    def list_for_user(user_id: UUID, page: int, per_page: int) -> tuple[list[OrderModel], int]:
        stmt = select(OrderModel).where(OrderModel.user_id == user_id)
        count_q = select(func.count()).select_from(OrderModel).where(
            OrderModel.user_id == user_id
        )
        total = int(db.session.scalar(count_q) or 0)

        page = max(page, 1)
        per_page = max(min(per_page, 100), 1)
        offset = (page - 1) * per_page

        rows = list(
            db.session.execute(
                stmt.order_by(OrderModel.created_at.desc()).offset(offset).limit(per_page)
            ).scalars()
        )
        return rows, total
