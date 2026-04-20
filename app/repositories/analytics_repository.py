from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.sql import Select

from app.extensions import db
from app.models.enums import OrderStatus
from app.models.order import OrderModel
from app.models.reservation import ReservationModel


class AnalyticsRepository:
    @staticmethod
    def get_general_metrics(
        restaurant_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        reservations_count = AnalyticsRepository._build_reservations_count_query(
            restaurant_id=restaurant_id,
            start_date=start_date,
            end_date=end_date,
        ).scalar_subquery()

        orders_count = AnalyticsRepository._build_orders_count_query(
            restaurant_id=restaurant_id,
            start_date=start_date,
            end_date=end_date,
        ).scalar_subquery()

        completed_revenue = AnalyticsRepository._build_completed_revenue_query(
            restaurant_id=restaurant_id,
            start_date=start_date,
            end_date=end_date,
        ).scalar_subquery()

        row = db.session.execute(
            db.select(
                reservations_count.label("total_reservations"),
                orders_count.label("total_orders"),
                completed_revenue.label("total_revenue"),
            )
        ).one()

        return {
            "totalReservations": int(row.total_reservations or 0),
            "totalOrders": int(row.total_orders or 0),
            "totalRevenue": Decimal(row.total_revenue or 0),
        }

    @staticmethod
    def get_daily_summary(
        restaurant_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict]:
        order_day = func.date(OrderModel.created_at)
        stmt = db.select(
            order_day.label("date"),
            func.count(OrderModel.id).label("orders"),
            func.coalesce(func.sum(OrderModel.total_amount), 0).label("revenue"),
        ).where(OrderModel.restaurant_id == restaurant_id)
        if start_date is not None:
            stmt = stmt.where(order_day >= start_date)
        if end_date is not None:
            stmt = stmt.where(order_day <= end_date)
        stmt = stmt.group_by(order_day).order_by(order_day)

        rows = db.session.execute(stmt).all()
        return [
            {
                "date": row.date.isoformat() if row.date else None,
                "orders": int(row.orders or 0),
                "revenue": Decimal(row.revenue or 0),
            }
            for row in rows
        ]

    @staticmethod
    def get_recent_activity(
        restaurant_id: int,
        limit: int = 10,
    ) -> dict:
        reservations_recent = (
            db.select(ReservationModel.id)
            .where(ReservationModel.restaurant_id == restaurant_id)
            .order_by(ReservationModel.created_at.desc())
            .limit(limit)
            .subquery()
        )
        orders_recent = (
            db.select(OrderModel.id)
            .where(OrderModel.restaurant_id == restaurant_id)
            .order_by(OrderModel.created_at.desc())
            .limit(limit)
            .subquery()
        )
        row = db.session.execute(
            db.select(
                db.select(func.count()).select_from(reservations_recent).scalar_subquery().label(
                    "recent_reservations"
                ),
                db.select(func.count()).select_from(orders_recent).scalar_subquery().label(
                    "recent_orders"
                ),
            )
        ).one()

        return {
            "recentReservations": int(row.recent_reservations or 0),
            "recentOrders": int(row.recent_orders or 0),
        }

    @staticmethod
    def _build_reservations_count_query(
        restaurant_id: int,
        start_date: date | None,
        end_date: date | None,
    ) -> Select:
        stmt = db.select(func.count(ReservationModel.id)).where(
            ReservationModel.restaurant_id == restaurant_id
        )
        if start_date is not None:
            stmt = stmt.where(ReservationModel.date >= start_date)
        if end_date is not None:
            stmt = stmt.where(ReservationModel.date <= end_date)
        return stmt

    @staticmethod
    def _build_orders_count_query(
        restaurant_id: int,
        start_date: date | None,
        end_date: date | None,
    ) -> Select:
        order_day = func.date(OrderModel.created_at)
        stmt = db.select(func.count(OrderModel.id)).where(OrderModel.restaurant_id == restaurant_id)
        if start_date is not None:
            stmt = stmt.where(order_day >= start_date)
        if end_date is not None:
            stmt = stmt.where(order_day <= end_date)
        return stmt

    @staticmethod
    def _build_completed_revenue_query(
        restaurant_id: int,
        start_date: date | None,
        end_date: date | None,
    ) -> Select:
        order_day = func.date(OrderModel.created_at)
        stmt = db.select(func.coalesce(func.sum(OrderModel.total_amount), 0)).where(
            OrderModel.restaurant_id == restaurant_id,
            OrderModel.status == OrderStatus.COMPLETED,
        )
        if start_date is not None:
            stmt = stmt.where(order_day >= start_date)
        if end_date is not None:
            stmt = stmt.where(order_day <= end_date)
        return stmt
