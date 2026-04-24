from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func

from app.extensions import db
from app.models.menu_item import MenuItemModel
from app.models.order import OrderModel
from app.models.order_item import OrderItemModel
from app.models.promotion import PromotionModel
from app.models.reservation import ReservationModel


class AnalyticsRepository:
    @staticmethod
    def get_orders_report(
        restaurant_id: UUID,
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
        restaurant_id: UUID,
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
        restaurant_id: UUID,
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
        restaurant_id: UUID,
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

    @staticmethod
    def get_popular_items(
        restaurant_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 10,
    ) -> list[dict]:
        order_day = func.date(OrderModel.created_at)
        base_filters = [OrderModel.restaurant_id == restaurant_id]
        if start_date is not None:
            base_filters.append(order_day >= start_date)
        if end_date is not None:
            base_filters.append(order_day <= end_date)

        rows = db.session.execute(
            db.select(
                OrderItemModel.menu_item_id.label("menu_item_id"),
                MenuItemModel.name.label("name"),
                func.sum(OrderItemModel.quantity).label("total_quantity"),
                func.count(OrderItemModel.id).label("order_count"),
                func.sum(OrderItemModel.quantity * OrderItemModel.unit_price).label("total_revenue"),
            )
            .join(OrderModel, OrderItemModel.order_id == OrderModel.id)
            .join(MenuItemModel, OrderItemModel.menu_item_id == MenuItemModel.id)
            .where(*base_filters)
            .group_by(OrderItemModel.menu_item_id, MenuItemModel.name)
            .order_by(func.sum(OrderItemModel.quantity).desc())
            .limit(limit)
        ).all()

        return [
            {
                "menuItemId": str(row.menu_item_id),
                "name": row.name,
                "totalQuantity": int(row.total_quantity or 0),
                "orderCount": int(row.order_count or 0),
                "totalRevenue": f"{Decimal(row.total_revenue or 0):.2f}",
            }
            for row in rows
        ]

    @staticmethod
    def get_occupancy_report(
        restaurant_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        base_filters = [ReservationModel.restaurant_id == restaurant_id]
        if start_date is not None:
            base_filters.append(ReservationModel.date >= start_date)
        if end_date is not None:
            base_filters.append(ReservationModel.date <= end_date)

        totals = db.session.execute(
            db.select(
                func.count(ReservationModel.id).label("total"),
                func.coalesce(func.sum(ReservationModel.party_size), 0).label("total_guests"),
            ).where(*base_filters)
        ).one()

        by_day = db.session.execute(
            db.select(
                ReservationModel.date.label("date"),
                func.count(ReservationModel.id).label("reservations"),
                func.coalesce(func.sum(ReservationModel.party_size), 0).label("guests"),
            )
            .where(*base_filters)
            .group_by(ReservationModel.date)
            .order_by(ReservationModel.date)
        ).all()

        return {
            "totalReservations": int(totals.total or 0),
            "totalGuests": int(totals.total_guests or 0),
            "byDay": [
                {
                    "date": row.date.isoformat() if row.date else None,
                    "reservations": int(row.reservations or 0),
                    "guests": int(row.guests or 0),
                }
                for row in by_day
            ],
        }

    @staticmethod
    def get_peak_hours(
        restaurant_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict]:
        base_filters = [ReservationModel.restaurant_id == restaurant_id]
        if start_date is not None:
            base_filters.append(ReservationModel.date >= start_date)
        if end_date is not None:
            base_filters.append(ReservationModel.date <= end_date)

        rows = db.session.execute(
            db.select(
                ReservationModel.time_slot.label("time_slot"),
                func.count(ReservationModel.id).label("reservations"),
                func.coalesce(func.sum(ReservationModel.party_size), 0).label("guests"),
            )
            .where(*base_filters)
            .group_by(ReservationModel.time_slot)
            .order_by(func.count(ReservationModel.id).desc())
        ).all()

        return [
            {
                "timeSlot": row.time_slot.isoformat() if row.time_slot else None,
                "reservations": int(row.reservations or 0),
                "guests": int(row.guests or 0),
            }
            for row in rows
        ]

    @staticmethod
    def get_promotions_report(
        restaurant_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict]:
        base_filters = [PromotionModel.restaurant_id == restaurant_id]
        if start_date is not None:
            base_filters.append(PromotionModel.start_date >= start_date)
        if end_date is not None:
            base_filters.append(PromotionModel.end_date <= end_date)

        rows = db.session.execute(
            db.select(PromotionModel).where(*base_filters).order_by(PromotionModel.created_at.desc())
        ).scalars()

        return [
            {
                "id": str(p.id),
                "title": p.title,
                "discountType": p.discount_type.value,
                "discountValue": f"{p.discount_value:.2f}",
                "startDate": p.start_date.isoformat(),
                "endDate": p.end_date.isoformat(),
                "isActive": p.is_active,
            }
            for p in rows
        ]
