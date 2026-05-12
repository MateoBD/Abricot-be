from datetime import date
from decimal import Decimal
from uuid import UUID

from app.exceptions.errors import NotFoundError, ValidationError
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.restaurant_repository import RestaurantRepository


class AnalyticsService:
    @staticmethod
    def get_orders_report(
        restaurant_id: UUID,
        start: str | None = None,
        end: str | None = None,
    ) -> dict:
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")

        start_date, end_date = AnalyticsService._parse_date_range(start=start, end=end)

        report = AnalyticsRepository.get_orders_report(
            restaurant_id=restaurant_id,
            start_date=start_date,
            end_date=end_date,
        )

        return {
            "restaurantId": str(restaurant_id),
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
            "totalOrders": report["totalOrders"],
            "totalRevenue": AnalyticsService._format_money(report["totalRevenue"]),
            "averageOrderValue": AnalyticsService._format_money(report["averageOrderValue"]),
            "ordersByStatus": report["ordersByStatus"],
            "revenueByDay": [
                {
                    "date": row["date"],
                    "revenue": AnalyticsService._format_money(row["revenue"]),
                    "orders": row["orders"],
                }
                for row in report["revenueByDay"]
            ],
        }

    @staticmethod
    def _parse_optional_date(value: str | None, field_name: str) -> date | None:
        if value is None:
            return None

        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise ValidationError(
                f"Invalid {field_name}. Expected format: YYYY-MM-DD.",
                {field_name: "Invalid date format"},
            ) from error

    @staticmethod
    def _parse_date_range(start: str | None, end: str | None) -> tuple[date | None, date | None]:
        if start is None and end is None:
            raise ValidationError(
                "Both start and end are required.",
                {
                    "start": "Required",
                    "end": "Required",
                },
            )

        if (start is None) != (end is None):
            raise ValidationError(
                "Both start and end must be provided together.",
                {
                    "start": "Required together with end",
                    "end": "Required together with start",
                },
            )

        start_date = AnalyticsService._parse_optional_date(start, "start")
        end_date = AnalyticsService._parse_optional_date(end, "end")

        if start_date and end_date and start_date > end_date:
            raise ValidationError(
                "The start date must be before or equal to the end date.",
                {"start": "Must be <= end"},
            )

        return start_date, end_date

    @staticmethod
    def get_general_metrics(
        restaurant_id: UUID,
        start: str | None = None,
        end: str | None = None,
    ) -> dict:
        """Get general metrics for a restaurant (orders, reservations, revenue)."""
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")

        start_date, end_date = AnalyticsService._parse_date_range(start=start, end=end)

        orders_data = AnalyticsRepository.get_orders_report(
            restaurant_id=restaurant_id,
            start_date=start_date,
            end_date=end_date,
        )

        reservations_data = AnalyticsRepository.get_reservations_metrics(
            restaurant_id=restaurant_id,
            start_date=start_date,
            end_date=end_date,
        )
        reservations_by_status = {
            row["status"]: row["count"]
            for row in reservations_data["reservationsByStatus"]
        }

        return {
            "restaurantId": str(restaurant_id),
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
            "totalOrders": orders_data["totalOrders"],
            "totalReservations": reservations_data["totalReservations"],
            "totalRevenue": AnalyticsService._format_money(orders_data["totalRevenue"]),
            "averageOrderValue": AnalyticsService._format_money(
                orders_data["averageOrderValue"]
            ),
            "totalCovers": reservations_data["totalGuests"],
            "completedReservations": reservations_by_status.get("COMPLETED", 0),
            "cancelledReservations": reservations_by_status.get("CANCELLED", 0),
            "noShowReservations": reservations_by_status.get("NO_SHOW", 0),
        }

    @staticmethod
    def get_occupancy_report(
        restaurant_id: UUID,
        start: str | None = None,
        end: str | None = None,
    ) -> dict:
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        start_date, end_date = AnalyticsService._parse_date_range(start=start, end=end)
        report = AnalyticsRepository.get_occupancy_report(
            restaurant_id=restaurant_id, start_date=start_date, end_date=end_date
        )
        return {
            "restaurantId": str(restaurant_id),
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
            **report,
        }

    @staticmethod
    def get_popular_items(
        restaurant_id: UUID,
        start: str | None = None,
        end: str | None = None,
        limit: int = 10,
    ) -> dict:
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        start_date, end_date = AnalyticsService._parse_date_range(start=start, end=end)
        items = AnalyticsRepository.get_popular_items(
            restaurant_id=restaurant_id,
            start_date=start_date,
            end_date=end_date,
            limit=max(1, min(limit, 100)),
        )
        return {
            "restaurantId": str(restaurant_id),
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
            "items": items,
        }

    @staticmethod
    def get_promotions_report(
        restaurant_id: UUID,
        start: str | None = None,
        end: str | None = None,
    ) -> dict:
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        start_date, end_date = AnalyticsService._parse_date_range(start=start, end=end)
        promotions = AnalyticsRepository.get_promotions_report(
            restaurant_id=restaurant_id, start_date=start_date, end_date=end_date
        )
        return {
            "restaurantId": str(restaurant_id),
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
            "promotions": promotions,
        }

    @staticmethod
    def get_peak_hours(
        restaurant_id: UUID,
        start: str | None = None,
        end: str | None = None,
    ) -> dict:
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        start_date, end_date = AnalyticsService._parse_date_range(start=start, end=end)
        hours = AnalyticsRepository.get_peak_hours(
            restaurant_id=restaurant_id, start_date=start_date, end_date=end_date
        )
        return {
            "restaurantId": str(restaurant_id),
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
            "peakHours": hours,
        }

    @staticmethod
    def _format_money(value: Decimal) -> str:
        return f"{value:.2f}"
