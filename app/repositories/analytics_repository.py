from datetime import date
from decimal import Decimal

from sqlalchemy import func

from app.extensions import db
from app.models.enums import OrderStatus
from app.models.order import OrderModel
from app.models.reservation import ReservationModel


class AnalyticsRepository:
    @staticmethod
    def count_reservations(
        restaurant_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> int:
        stmt = db.select(func.count(ReservationModel.id)).where(
            ReservationModel.restaurant_id == restaurant_id
        )
        if start_date is not None:
            stmt = stmt.where(ReservationModel.date >= start_date)
        if end_date is not None:
            stmt = stmt.where(ReservationModel.date <= end_date)

        result = db.session.execute(stmt).scalar_one()
        return int(result or 0)

    @staticmethod
    def count_orders(
        restaurant_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> int:
        stmt = db.select(func.count(OrderModel.id)).where(OrderModel.restaurant_id == restaurant_id)
        if start_date is not None:
            stmt = stmt.where(func.date(OrderModel.created_at) >= start_date)
        if end_date is not None:
            stmt = stmt.where(func.date(OrderModel.created_at) <= end_date)

        result = db.session.execute(stmt).scalar_one()
        return int(result or 0)

    @staticmethod
    def sum_revenue(
        restaurant_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Decimal:
        stmt = db.select(func.coalesce(func.sum(OrderModel.total_amount), 0)).where(
            OrderModel.restaurant_id == restaurant_id,
            OrderModel.status == OrderStatus.COMPLETED,
        )
        if start_date is not None:
            stmt = stmt.where(func.date(OrderModel.created_at) >= start_date)
        if end_date is not None:
            stmt = stmt.where(func.date(OrderModel.created_at) <= end_date)

        result = db.session.execute(stmt).scalar_one()
        return Decimal(result)
