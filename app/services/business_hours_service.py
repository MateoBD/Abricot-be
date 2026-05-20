import logging
from datetime import date, time
from uuid import UUID

from app.exceptions.errors import NotFoundError, ValidationError
from app.repositories.business_hours_repository import BusinessHoursRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.utils.list_envelope import list_envelope

logger = logging.getLogger(__name__)

# dayOfWeek: 0 = Monday (Lunes) … 6 = Sunday (Domingo). Matches Python date.weekday().
_DAY_NAMES = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}


def _normalize_day_input(row: dict) -> dict:
    """Accept owner UI shape: isClosed/isOpen plus one interval per day."""
    normalized = dict(row)
    if "isOpen" in row:
        normalized["isClosed"] = not bool(row.get("isOpen"))

    raw_ranges = row.get("ranges")
    if not raw_ranges:
        open_time = row.get("openTime") or row.get("opensAt")
        close_time = row.get("closeTime") or row.get("closesAt")
        if open_time and close_time:
            normalized["ranges"] = [{"opensAt": open_time, "closesAt": close_time}]
    return normalized


def _parse_time(value: str | None, field: str) -> time | None:
    if value is None:
        return None
    try:
        return time.fromisoformat(value)
    except ValueError as err:
        raise ValidationError(
            f"Invalid {field}. Expected HH:MM or HH:MM:SS.", {field: "Invalid time format"}
        ) from err


def _validate_ranges(day: int, ranges: list[dict]) -> list[dict]:
    """Parse, validate, and sort a list of range dicts.

    Each input dict must have `opensAt` and `closesAt` string keys.
    Returns a list of dicts with `opens_at` / `closes_at` time objects,
    sorted by opens_at and verified to be non-overlapping.
    """
    parsed: list[dict] = []
    for r in ranges:
        opens_at = _parse_time(r.get("opensAt"), "opensAt")
        closes_at = _parse_time(r.get("closesAt"), "closesAt")

        if opens_at is None or closes_at is None:
            raise ValidationError(
                f"Day {day}: opensAt and closesAt are required in every range.",
                {"ranges": "opensAt and closesAt required"},
            )
        if opens_at == closes_at:
            raise ValidationError(
                f"Day {day}: opensAt and closesAt cannot be the same.",
                {"ranges": "opensAt must differ from closesAt"},
            )
        if closes_at < opens_at:
            raise ValidationError(
                f"Day {day}: closes_at must be after opens_at "
                "(midnight-crossing is not supported for multi-range days).",
                {"ranges": "closesAt must be after opensAt"},
            )
        parsed.append({"opens_at": opens_at, "closes_at": closes_at})

    # Sort by opening time for deterministic ordering and overlap detection.
    parsed.sort(key=lambda r: r["opens_at"])

    # Detect overlapping ranges: range[i].closes_at must be <= range[i+1].opens_at.
    for i in range(len(parsed) - 1):
        a, b = parsed[i], parsed[i + 1]
        if a["closes_at"] > b["opens_at"]:
            raise ValidationError(
                f"Day {day}: ranges overlap — "
                f"{a['opens_at'].isoformat()}–{a['closes_at'].isoformat()} "
                f"overlaps with {b['opens_at'].isoformat()}–{b['closes_at'].isoformat()}.",
                {"ranges": "Overlapping ranges"},
            )

    return parsed


def _group_to_days(
    rows: list,
) -> list[dict]:
    """Group flat range rows into a 7-entry list keyed by day_of_week."""
    by_day: dict[int, list] = {d: [] for d in range(7)}
    for row in rows:
        by_day[row.day_of_week].append(row)

    result = []
    for day in range(7):
        day_ranges = by_day[day]
        is_closed = len(day_ranges) == 0
        first_range = day_ranges[0] if day_ranges else None
        result.append(
            {
                "dayOfWeek": day,
                "dayName": _DAY_NAMES[day],
                "isClosed": is_closed,
                "isOpen": not is_closed,
                "openTime": first_range.opens_at.isoformat() if first_range else None,
                "closeTime": first_range.closes_at.isoformat() if first_range else None,
                "ranges": [
                    {
                        "opensAt": r.opens_at.isoformat(),
                        "closesAt": r.closes_at.isoformat(),
                    }
                    for r in day_ranges
                ],
            }
        )
    return result


class BusinessHoursService:
    @staticmethod
    def get_all(restaurant_id: UUID) -> dict:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        rows = BusinessHoursRepository.get_all(restaurant_id)
        return list_envelope(_group_to_days(rows))

    @staticmethod
    def bulk_update(restaurant_id: UUID, hours_data: list[dict]) -> dict:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")

        from app.extensions import db

        for row in hours_data:
            normalized_row = _normalize_day_input(row)
            day = normalized_row.get("dayOfWeek")
            if day is None or not isinstance(day, int) or day < 0 or day > 6:
                raise ValidationError(
                    "dayOfWeek must be an integer between 0 (Lunes) and 6 (Domingo).",
                    {"dayOfWeek": "Must be 0–6"},
                )

            is_closed = bool(normalized_row.get("isClosed", False))

            if is_closed:
                BusinessHoursRepository.replace_day(restaurant_id, day, [])
            else:
                raw_ranges = normalized_row.get("ranges") or []
                if len(raw_ranges) > 1:
                    raise ValidationError(
                        f"Day {day}: only one opening interval per day is supported.",
                        {"ranges": "At most one range"},
                    )
                if not raw_ranges:
                    raise ValidationError(
                        f"Day {day}: openTime and closeTime are required when the day is open.",
                        {"ranges": "Required when open"},
                    )
                validated = _validate_ranges(day, raw_ranges)
                BusinessHoursRepository.replace_day(restaurant_id, day, validated)

        db.session.commit()
        rows = BusinessHoursRepository.get_all(restaurant_id)
        logger.info("Business hours updated for restaurant_id=%s", restaurant_id)
        return list_envelope(_group_to_days(rows))

    # ── Availability helpers ──────────────────────────────────────────────────

    @staticmethod
    def is_open_on(restaurant_id: UUID, on_date: date) -> bool:
        day_of_week = on_date.weekday()
        rows = BusinessHoursRepository.get_for_date(restaurant_id, day_of_week)
        return len(rows) > 0

    @staticmethod
    def get_time_ranges(
        restaurant_id: UUID, on_date: date
    ) -> list[tuple[time, time]]:
        """Return all (opens_at, closes_at) pairs for a given date, in order.

        Returns an empty list if the restaurant is closed on that day.
        """
        day_of_week = on_date.weekday()
        rows = BusinessHoursRepository.get_for_date(restaurant_id, day_of_week)
        return [(r.opens_at, r.closes_at) for r in rows]
