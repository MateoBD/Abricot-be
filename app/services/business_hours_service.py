import logging
from datetime import date, time
from uuid import UUID

from app.exceptions.errors import NotFoundError, ValidationError
from app.repositories.business_hours_repository import BusinessHoursRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.utils.list_envelope import list_envelope

logger = logging.getLogger(__name__)

_DAY_NAMES = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}


def _parse_time(value: str | None, field: str) -> time | None:
    if value is None:
        return None
    try:
        return time.fromisoformat(value)
    except ValueError as err:
        raise ValidationError(
            f"Invalid {field}. Expected HH:MM or HH:MM:SS.", {field: "Invalid time format"}
        ) from err


class BusinessHoursService:
    @staticmethod
    def get_all(restaurant_id: UUID) -> dict:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        hours = BusinessHoursRepository.get_all(restaurant_id)
        return list_envelope([h.to_dict() for h in hours])

    @staticmethod
    def bulk_update(restaurant_id: UUID, hours_data: list[dict]) -> dict:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")

        parsed: list[dict] = []
        for row in hours_data:
            day = row.get("dayOfWeek")
            if day is None or not isinstance(day, int) or day < 0 or day > 6:
                raise ValidationError(
                    "dayOfWeek must be an integer between 0 (Monday) and 6 (Sunday).",
                    {"dayOfWeek": "Must be 0–6"},
                )
            is_closed = bool(row.get("isClosed", False))
            opens_at = None if is_closed else _parse_time(row.get("opensAt"), "opensAt")
            closes_at = None if is_closed else _parse_time(row.get("closesAt"), "closesAt")
            if not is_closed and (opens_at is None or closes_at is None):
                raise ValidationError(
                    f"opensAt and closesAt are required when isClosed is false (day={day}).",
                    {"opensAt": "Required", "closesAt": "Required"},
                )
            if not is_closed and opens_at and closes_at and opens_at >= closes_at:
                raise ValidationError(
                    f"opensAt must be before closesAt (day={day}).",
                    {"opensAt": "Must be before closesAt"},
                )
            parsed.append(
                {
                    "day_of_week": day,
                    "opens_at": opens_at,
                    "closes_at": closes_at,
                    "is_closed": is_closed,
                }
            )

        updated = BusinessHoursRepository.upsert_bulk(restaurant_id, parsed)
        logger.info("Business hours updated: restaurant_id=%s", restaurant_id)
        return list_envelope([h.to_dict() for h in updated])

    @staticmethod
    def is_open_on(restaurant_id: UUID, on_date: date) -> bool:
        day_of_week = on_date.weekday()
        hours = BusinessHoursRepository.get_for_date(restaurant_id, day_of_week)
        if hours is None:
            return False
        return not hours.is_closed

    @staticmethod
    def get_time_range(
        restaurant_id: UUID, on_date: date
    ) -> tuple[time, time] | None:
        day_of_week = on_date.weekday()
        hours = BusinessHoursRepository.get_for_date(restaurant_id, day_of_week)
        if hours is None or hours.is_closed or hours.opens_at is None or hours.closes_at is None:
            return None
        return hours.opens_at, hours.closes_at
