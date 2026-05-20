import logging
from datetime import date, datetime, time, timedelta
from itertools import combinations
from uuid import UUID

from app.exceptions.errors import ConflictError, NotFoundError, ValidationError
from app.models.table import TableModel
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.reservation_table_repository import ReservationTableRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.table_repository import TableRepository
from app.services.business_hours_service import BusinessHoursService

logger = logging.getLogger(__name__)

_SLOT_STEP_MINUTES = 30

# dayOfWeek convention (aligned with Python date.weekday() and owner UI):
# 0 = Monday (Lunes) … 6 = Sunday (Domingo). Not JavaScript getDay() (0 = Sunday).


def _window_minutes(opens_at: time, closes_at: time) -> int:
    base_date = date.today()
    start = datetime.combine(base_date, opens_at)
    end = datetime.combine(base_date, closes_at)
    if closes_at <= opens_at:
        end += timedelta(days=1)
    return max(0, int((end - start).total_seconds() // 60))


def _slots_for_range(opens_at: time, closes_at: time, slot_duration: int) -> list[time]:
    """Generate start times every 30 minutes while a reservation of slot_duration fits."""
    window_minutes = _window_minutes(opens_at, closes_at)
    if window_minutes < _SLOT_STEP_MINUTES:
        return []

    # A 90-minute default slot must not erase all slots on short lunch windows.
    effective_duration = min(max(slot_duration, _SLOT_STEP_MINUTES), window_minutes)

    slots: list[time] = []
    base_date = date.today()
    current = datetime.combine(base_date, opens_at)
    closes_at_datetime = datetime.combine(base_date, closes_at)
    if closes_at <= opens_at:
        closes_at_datetime += timedelta(days=1)
    end = closes_at_datetime - timedelta(minutes=effective_duration)
    step = timedelta(minutes=_SLOT_STEP_MINUTES)
    while current <= end:
        slots.append(current.time())
        current += step
    return slots


class AvailabilityService:
    @staticmethod
    def get_occupied_table_ids_at(
        restaurant_id: UUID,
        on_date: date,
        time_slot: time,
        *,
        exclude_reservation_id: UUID | None = None,
    ) -> set[UUID]:
        return ReservationRepository.get_occupied_table_ids_at(
            restaurant_id=restaurant_id,
            on_date=on_date,
            time_slot=time_slot,
            exclude_reservation_id=exclude_reservation_id,
        )

    @staticmethod
    def find_table_assignment(
        restaurant_id: UUID,
        on_date: date,
        time_slot: time,
        party_size: int,
        *,
        lock_rows: bool = False,
    ) -> list[TableModel] | None:
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            return None

        if lock_rows:
            # Locking table rows first serializes concurrent assignment attempts for the same restaurant.
            active_tables = TableRepository.get_active_for_update(restaurant_id)
        else:
            active_tables = TableRepository.get_active(restaurant_id)
        occupied = AvailabilityService.get_occupied_table_ids_at(
            restaurant_id,
            on_date,
            time_slot,
        )
        available = [t for t in active_tables if t.id not in occupied]

        # Try single table first (least waste)
        single_candidates = [t for t in available if t.capacity >= party_size]
        if single_candidates:
            best = min(single_candidates, key=lambda t: t.capacity)
            return [best]

        if not restaurant.allow_table_joining:
            return None

        # Try joined tables (joinable only), fewest tables with minimum wasted capacity
        joinable = [t for t in available if t.is_joinable]
        best_combo: list[TableModel] | None = None
        best_waste = float("inf")

        for combo_size in range(2, len(joinable) + 1):
            for combo in combinations(joinable, combo_size):
                total_cap = sum(t.capacity for t in combo)
                if total_cap >= party_size:
                    waste = total_cap - party_size
                    if waste < best_waste:
                        best_waste = waste
                        best_combo = list(combo)
            if best_combo is not None:
                break  # smallest combo found — stop iterating larger sizes

        return best_combo

    @staticmethod
    def _empty_reason(
        restaurant_id: UUID,
        *,
        on_date: date,
        party_size: int,
        allow_table_joining: bool,
        time_ranges: list[tuple[time, time]],
        candidate_slots: list[time],
        available_results: list[dict],
    ) -> str | None:
        if not time_ranges:
            return "CLOSED_OR_NO_HOURS"

        active_tables = TableRepository.get_active(restaurant_id)
        if not active_tables:
            return "NO_TABLES"

        if not any(table.capacity >= party_size for table in active_tables):
            if not allow_table_joining:
                return "NO_TABLES_FOR_PARTY_SIZE"
            joinable = [table for table in active_tables if table.is_joinable]
            if sum(table.capacity for table in joinable) < party_size:
                return "NO_TABLES_FOR_PARTY_SIZE"

        if candidate_slots and not available_results:
            return "ALL_SLOTS_OCCUPIED"

        if not candidate_slots:
            return "NO_SLOTS_IN_HOURS"

        return None

    @staticmethod
    def get_available_slots(
        restaurant_id: UUID, on_date: date, party_size: int
    ) -> list[dict]:
        return AvailabilityService.get_availability_payload(
            restaurant_id,
            on_date,
            party_size,
        )["slots"]

    @staticmethod
    def get_availability_payload(
        restaurant_id: UUID, on_date: date, party_size: int
    ) -> dict:
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")

        if party_size < 1:
            raise ValidationError("partySize must be at least 1.", {"partySize": "Must be >= 1"})

        time_ranges = BusinessHoursService.get_time_ranges(restaurant_id, on_date)
        slot_duration = restaurant.default_slot_duration_minutes

        candidate_slots: list[time] = []
        for opens_at, closes_at in time_ranges:
            candidate_slots.extend(_slots_for_range(opens_at, closes_at, slot_duration))

        result: list[dict] = []
        for slot in candidate_slots:
            assignment = AvailabilityService.find_table_assignment(
                restaurant_id, on_date, slot, party_size
            )
            if assignment is not None:
                result.append(
                    {
                        "timeSlot": slot.isoformat(),
                        "available": True,
                        "isAvailable": True,
                        "tableAssignment": [
                            {
                                "tableId": str(t.id),
                                "number": t.number,
                                "capacity": t.capacity,
                            }
                            for t in assignment
                        ],
                    }
                )

        empty_reason = AvailabilityService._empty_reason(
            restaurant_id,
            on_date=on_date,
            party_size=party_size,
            allow_table_joining=restaurant.allow_table_joining,
            time_ranges=time_ranges,
            candidate_slots=candidate_slots,
            available_results=result,
        )

        payload: dict = {
            "date": on_date.isoformat(),
            "partySize": party_size,
            "dayOfWeek": on_date.weekday(),
            "slots": result,
        }
        if empty_reason:
            payload["emptyReason"] = empty_reason
        return payload

    @staticmethod
    def assign_tables_for_reservation(
        reservation_id: UUID,
        table_ids: list[UUID],
    ) -> None:
        """
        Assign tables to a reservation within an explicit transaction with row-level locking.
        
        This method ensures atomicity and prevents concurrent double-assignment by:
        1. Locking the target tables with SELECT ... FOR UPDATE
        2. Verifying availability again within the transaction (re-check)
        3. Creating the reservation_table associations
        4. Committing atomically
        """
        try:
            # Get reservation to access restaurant_id
            reservation = ReservationRepository.get_by_id(reservation_id)
            if not reservation:
                raise NotFoundError(f"Reservation with id={reservation_id} not found.")
            
            # Lock target tables for exclusive access
            TableRepository.get_active_for_update(reservation.restaurant_id)
            
            # Re-check occupancy within transaction to catch any races (defense-in-depth against TOCTOU)
            restaurant = RestaurantRepository.get_by_id(reservation.restaurant_id)
            if not restaurant:
                raise NotFoundError(f"Restaurant with id={reservation.restaurant_id} not found.")
            
            occupied = AvailabilityService.get_occupied_table_ids_at(
                reservation.restaurant_id,
                reservation.date,
                reservation.time_slot,
                exclude_reservation_id=reservation_id,
            )
            conflicts = [tid for tid in table_ids if tid in occupied]
            if conflicts:
                raise ConflictError(
                    "One or more tables became occupied during assignment.",
                    {"tableIds": "Conflict detected"},
                )
            
            # Assign tables within transaction
            ReservationTableRepository.create_bulk(
                reservation_id, table_ids, auto_commit=False
            )
            ReservationRepository.commit()
        except Exception:
            ReservationRepository.rollback()
            raise
