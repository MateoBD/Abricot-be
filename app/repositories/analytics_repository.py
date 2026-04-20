from datetime import date
from decimal import Decimal

from sqlalchemy import func

from app.extensions import db
from app.models.order import OrderModel
from app.models.reservation import ReservationModel


class AnalyticsRepository:
    @staticmethod
    def get_orders_report(
        restaurant_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        order_day = func.date(OrderModel.created_at)
        base_filters = [OrderModel.restaurant_id == restaurant_id]
        if start_date is not None:
            base_filters.append(order_day >= start_date)
        if end_date is not None:
            base_filters.append(order_day <= end_date)

        totals = db.session.execute(
            db.select(
                func.count(OrderModel.id).label("total_orders"),
                func.coalesce(func.sum(OrderModel.total_amount), 0).label("total_revenue"),
            ).where(*base_filters)
        ).one()

        status_rows = db.session.execute(
            db.select(
                OrderModel.status.label("status"),
                func.count(OrderModel.id).label("count"),
            )
            .where(*base_filters)
            .group_by(OrderModel.status)
            .order_by(OrderModel.status)
        ).all()

        by_day_rows = db.session.execute(
            db.select(
                order_day.label("date"),
                func.coalesce(func.sum(OrderModel.total_amount), 0).label("revenue"),
                func.count(OrderModel.id).label("orders"),
            )
            .where(*base_filters)
            .group_by(order_day)
            .order_by(order_day)
        ).all()

        total_orders = int(totals.total_orders or 0)
        total_revenue = Decimal(totals.total_revenue or 0)
        average_order_value = total_revenue / total_orders if total_orders else Decimal("0")

        return {
            "totalOrders": total_orders,
            "totalRevenue": total_revenue,
            "averageOrderValue": average_order_value,
            "ordersByStatus": [
                {
                    "status": row.status.value if hasattr(row.status, "value") else str(row.status),
                    "count": int(row.count or 0),
                }
                for row in status_rows
            ],
            "revenueByDay": [
                {
                    "date": row.date.isoformat() if row.date else None,
                    "revenue": Decimal(row.revenue or 0),
                    "orders": int(row.orders or 0),
                }
                for row in by_day_rows
            ],
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
    def get_reservations_metrics(
        restaurant_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        """Get reservations metrics for a restaurant within a date range."""
        reservation_day = func.date(ReservationModel.created_at)
        base_filters = [ReservationModel.restaurant_id == restaurant_id]
        if start_date is not None:
            base_filters.append(reservation_day >= start_date)
        if end_date is not None:
            base_filters.append(reservation_day <= end_date)

        totals = db.session.execute(
            db.select(
                func.count(ReservationModel.id).label("total_reservations"),
                func.coalesce(func.sum(ReservationModel.party_size), 0).label("total_guests"),
            ).where(*base_filters)
        ).one()

        status_rows = db.session.execute(
            db.select(
                ReservationModel.status.label("status"),
                func.count(ReservationModel.id).label("count"),
            )
            .where(*base_filters)
            .group_by(ReservationModel.status)
            .order_by(ReservationModel.status)
        ).all()

        return {
            "totalReservations": int(totals.total_reservations or 0),
            "totalGuests": int(totals.total_guests or 0),
            "reservationsByStatus": [
                {
                    "status": row.status.value if hasattr(row.status, "value") else str(row.status),
                    "count": int(row.count or 0),
                }
                for row in status_rows
            ],
        }
