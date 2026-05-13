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
        
        # Ensure all 7 days exist
        BusinessHoursService._ensure_all_days_exist(restaurant_id)
        
        # Refresh session to see latest changes
        from app.extensions import db
        db.session.expunge_all()
        
        hours = BusinessHoursRepository.get_all(restaurant_id)
        logger.info(f"Loaded {len(hours)} business hours for restaurant {restaurant_id}")
        return list_envelope([h.to_dict() for h in hours])

    @staticmethod
    def _ensure_all_days_exist(restaurant_id: UUID) -> None:
        """Ensure all 7 days (0-6) exist for the restaurant."""
        from app.extensions import db
        
        existing_hours = BusinessHoursRepository.get_all(restaurant_id)
        existing_days = {h.day_of_week for h in existing_hours}
        logger.info(f"Existing days for restaurant {restaurant_id}: {sorted(existing_days)}")
        
        # Create missing days (default: closed)
        missing_days = [d for d in range(7) if d not in existing_days]
        if missing_days:
            logger.info(f"Creating missing days for restaurant {restaurant_id}: {missing_days}")
            data = [
                {
                    "day_of_week": day,
                    "opens_at": None,
                    "closes_at": None,
                    "is_closed": True,
                }
                for day in missing_days
            ]
            BusinessHoursRepository.upsert_bulk(restaurant_id, data)
            db.session.expunge_all()
            logger.info(f"Successfully created missing days for restaurant {restaurant_id}")
        else:
            logger.info(f"All 7 days already exist for restaurant {restaurant_id}")

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
            
            # If closed, ignore opensAt/closesAt (treat as None)
            if is_closed:
                opens_at = None
                closes_at = None
            else:
                # If open, get the time values (may be None, which will trigger validation error below)
                opens_at = _parse_time(row.get("opensAt"), "opensAt")
                closes_at = _parse_time(row.get("closesAt"), "closesAt")
                
                # Validate that times are provided when open
                if opens_at is None or closes_at is None:
                    raise ValidationError(
                        f"opensAt and closesAt are required when isClosed is false (day={day}).",
                        {"opensAt": "Required", "closesAt": "Required"},
                    )
                
                # Validate that opening time is before closing time
                # Allow crossing midnight (e.g., 21:00 - 03:00)
                if opens_at == closes_at:
                    raise ValidationError(
                        f"opensAt and closesAt cannot be the same (day={day}).",
                        {"opensAt": "Must differ from closesAt"},
                    )
                
                # If closing time is earlier than opening, assume it crosses midnight (valid)
                # Otherwise, validate that opening is before closing
                if closes_at < opens_at:
                    logger.debug(f"Day {day}: crossing midnight ({opens_at} - {closes_at})")
                else:
                    # Normal case: opening before closing on same day
                    pass
            
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
