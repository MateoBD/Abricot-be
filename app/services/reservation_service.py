import secrets
import string
from datetime import date, time
import logging
from uuid import UUID

from app.exceptions.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.enums import ReservationSource, ReservationStatus
from app.models.reservation import ReservationModel
from app.models.enums import UserRole
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.reservation_table_repository import ReservationTableRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.restaurant_admin_repository import RestaurantAdminRepository
from app.repositories.user_repository import UserRepository
from app.utils.list_envelope import paginated_list_envelope

logger = logging.getLogger(__name__)
_CONFIRMATION_CODE_LENGTH = 8
_CONFIRMATION_CODE_ATTEMPTS = 5


def _generate_confirmation_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(_CONFIRMATION_CODE_LENGTH))


def _generate_unique_confirmation_code() -> str:
    for _ in range(_CONFIRMATION_CODE_ATTEMPTS):
        candidate = _generate_confirmation_code()
        if not ReservationRepository.get_by_code(candidate):
            return candidate
    raise ConflictError(
        "Could not generate a unique confirmation code. Please try again.",
        {"confirmationCode": "Could not allocate unique code"},
    )


def _time_in_business_range(time_slot: time, opens_at: time, closes_at: time) -> bool:
    if opens_at < closes_at:
        return opens_at <= time_slot < closes_at
    return time_slot >= opens_at or time_slot < closes_at


def _matching_business_range(
    time_slot: time,
    time_ranges: list[tuple[time, time]],
) -> tuple[time, time] | None:
    for opens_at, closes_at in time_ranges:
        if _time_in_business_range(time_slot, opens_at, closes_at):
            return opens_at, closes_at
    return None


def _format_business_ranges(time_ranges: list[tuple[time, time]]) -> str:
    return ", ".join(
        f"{opens_at.isoformat()} - {closes_at.isoformat()}"
        for opens_at, closes_at in time_ranges
    )


class ReservationService:
    @staticmethod
    def _is_restaurant_admin_or_super_admin(user_id: UUID, restaurant_id: UUID) -> bool:
        user = UserRepository.get_by_id(user_id)
        if not user:
            return False
        if user.role == UserRole.SUPER_ADMIN:
            return True
        if user.role != UserRole.RESTAURANT_ADMIN:
            return False
        return RestaurantAdminRepository.is_admin(
            user_id=user_id,
            restaurant_id=restaurant_id,
        )

    @staticmethod
    def _assert_can_access_reservation(
        reservation: ReservationModel,
        requesting_user_id: UUID,
        *,
        message: str,
    ) -> None:
        if reservation.user_id == requesting_user_id:
            return
        if ReservationService._is_restaurant_admin_or_super_admin(
            requesting_user_id,
            reservation.restaurant_id,
        ):
            return
        raise ForbiddenError(
            message,
            {
                "authorization": (
                    "User must be reservation owner, SUPER_ADMIN, or a RESTAURANT_ADMIN assigned "
                    "to this restaurant."
                )
            },
        )

    @staticmethod
    def parse_required_date(value: str) -> date:
        try:
            return date.fromisoformat(value)
        except (TypeError, ValueError) as error:
            raise ValidationError(
                "Invalid date. Expected format: YYYY-MM-DD.",
                {"date": "Invalid date format"},
            ) from error

    @staticmethod
    def parse_required_time(value: str) -> time:
        try:
            parsed = time.fromisoformat(value)
            return parsed.replace(tzinfo=None)
        except (TypeError, ValueError) as error:
            raise ValidationError(
                "Invalid timeSlot. Expected format: HH:MM or HH:MM:SS.",
                {"timeSlot": "Invalid time format"},
            ) from error

    @staticmethod
    def parse_required_admin_source(value: str) -> ReservationSource:
        try:
            source = ReservationSource(value)
        except (TypeError, ValueError) as error:
            raise ValidationError(
                "Invalid source.",
                {"source": "Must be one of: PHONE, EVENT"},
            ) from error

        if source not in (ReservationSource.PHONE, ReservationSource.EVENT):
            raise ValidationError(
                "Invalid source.",
                {"source": "Must be one of: PHONE, EVENT"},
            )
        return source

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
    def _parse_optional_status(value: str | None) -> ReservationStatus | None:
        if value is None:
            return None
        try:
            return ReservationStatus(value)
        except ValueError as error:
            raise ValidationError(
                "Invalid status.",
                {"status": "Must be one of: CONFIRMED, CANCELLED, COMPLETED, NO_SHOW"},
            ) from error

    @staticmethod
    def _parse_optional_source(value: str | None) -> ReservationSource | None:
        if value is None:
            return None
        try:
            return ReservationSource(value)
        except ValueError as error:
            raise ValidationError(
                "Invalid source.",
                {"source": "Must be one of: ONLINE, PHONE, EVENT"},
            ) from error

    @staticmethod
    def _to_payload(reservation: ReservationModel) -> dict:
        return reservation.to_dict()

    @staticmethod
    def list_for_restaurant(
        restaurant_id: UUID,
        *,
        on_date: str | None = None,
        status: str | None = None,
        source: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")

        parsed_date = ReservationService._parse_optional_date(on_date, "date")
        parsed_status = ReservationService._parse_optional_status(status)
        parsed_source = ReservationService._parse_optional_source(source)

        filters = {
            "date_from": parsed_date,
            "date_to": parsed_date,
            "status": parsed_status,
            "source": parsed_source,
        }

        rows, total = ReservationRepository.list_for_restaurant(
            restaurant_id=restaurant_id,
            filters=filters,
            page=page,
            per_page=per_page,
        )
        data = [ReservationService._to_payload(row) for row in rows]
        logger.info(
            f"Reservations listed: restaurant_id={restaurant_id} total={total} page={page} per_page={per_page}"
        )
        return paginated_list_envelope(data, total=total, page=page, per_page=per_page)

    @staticmethod
    def create(
        restaurant_id: UUID,
        user_id: UUID,
        party_size: int,
        on_date: date,
        time_slot: time,
        notes: str | None = None,
    ) -> dict:
        from app.services.availability_service import AvailabilityService
        from app.services.business_hours_service import BusinessHoursService

        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        if not isinstance(party_size, int):
            raise ValidationError("partySize must be an integer.", {"partySize": "Invalid type"})
        if party_size < 1:
            raise ValidationError("partySize must be at least 1.", {"partySize": "Must be >= 1"})

        # Validate that restaurant is open on the requested date
        if not BusinessHoursService.is_open_on(restaurant_id, on_date):
            raise ValidationError(
                f"Restaurant is closed on {on_date.isoformat()}.",
                {"date": "Restaurant is closed"},
            )

        # Validate that time_slot is within operating hours
        time_ranges = BusinessHoursService.get_time_ranges(restaurant_id, on_date)
        if not time_ranges:
            raise ValidationError(
                f"No operating hours defined for {on_date.isoformat()}.",
                {"date": "No operating hours"},
            )
        matching_range = _matching_business_range(time_slot, time_ranges)
        if matching_range is None:
            raise ValidationError(
                f"Time slot {time_slot.isoformat()} is outside operating hours ({_format_business_ranges(time_ranges)}).",
                {"timeSlot": "Outside operating hours"},
            )

        assignment = AvailabilityService.find_table_assignment(
            restaurant_id,
            on_date,
            time_slot,
            party_size,
            lock_rows=True,
        )
        if assignment is None:
            raise ConflictError(
                "No tables available for the requested date, time, and party size.",
                {"timeSlot": "Not available"},
            )

        code = _generate_unique_confirmation_code()
        reservation = ReservationModel(
            restaurant_id=restaurant_id,
            user_id=user_id,
            party_size=party_size,
            date=on_date,
            time_slot=time_slot,
            source=ReservationSource.ONLINE,
            status=ReservationStatus.CONFIRMED,
            notes=notes,
            confirmation_code=code,
        )
        try:
            ReservationRepository.create(reservation, auto_commit=False)
            ReservationTableRepository.create_bulk(
                reservation.id,
                [t.id for t in assignment],
                auto_commit=False,
            )
            ReservationRepository.commit()
        except Exception:
            ReservationRepository.rollback()
            raise
        logger.info("Reservation created: id=%s code=%s", reservation.id, code)
        return ReservationService._to_payload(reservation)

    @staticmethod
    def create_guest_online(
        restaurant_id: UUID,
        party_size: int,
        on_date: date,
        time_slot: time,
        guest_name: str,
        guest_email: str,
        guest_phone: str | None = None,
        notes: str | None = None,
    ) -> dict:
        from app.services.availability_service import AvailabilityService
        from app.services.business_hours_service import BusinessHoursService

        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")

        normalized_guest_name = (guest_name or "").strip()
        normalized_guest_email = (guest_email or "").strip()
        normalized_guest_phone = (guest_phone or "").strip() or None
        if not normalized_guest_name:
            raise ValidationError("guestName is required.", {"guestName": "Required"})
        if not normalized_guest_email:
            raise ValidationError("guestEmail is required.", {"guestEmail": "Required"})
        if not isinstance(party_size, int):
            raise ValidationError("partySize must be an integer.", {"partySize": "Invalid type"})
        if party_size < 1:
            raise ValidationError("partySize must be at least 1.", {"partySize": "Must be >= 1"})

        if not BusinessHoursService.is_open_on(restaurant_id, on_date):
            raise ValidationError(
                f"Restaurant is closed on {on_date.isoformat()}.",
                {"date": "Restaurant is closed"},
            )

        time_ranges = BusinessHoursService.get_time_ranges(restaurant_id, on_date)
        if not time_ranges:
            raise ValidationError(
                f"No operating hours defined for {on_date.isoformat()}.",
                {"date": "No operating hours"},
            )
        matching_range = _matching_business_range(time_slot, time_ranges)
        if matching_range is None:
            raise ValidationError(
                f"Time slot {time_slot.isoformat()} is outside operating hours ({_format_business_ranges(time_ranges)}).",
                {"timeSlot": "Outside operating hours"},
            )

        assignment = AvailabilityService.find_table_assignment(
            restaurant_id,
            on_date,
            time_slot,
            party_size,
            lock_rows=True,
        )
        if assignment is None:
            raise ConflictError(
                "No tables available for the requested date, time, and party size.",
                {"timeSlot": "Not available"},
            )

        code = _generate_unique_confirmation_code()
        reservation = ReservationModel(
            restaurant_id=restaurant_id,
            user_id=None,
            guest_name=normalized_guest_name,
            guest_phone=normalized_guest_phone,
            guest_email=normalized_guest_email,
            party_size=party_size,
            date=on_date,
            time_slot=time_slot,
            source=ReservationSource.ONLINE,
            status=ReservationStatus.CONFIRMED,
            notes=notes,
            confirmation_code=code,
        )
        try:
            ReservationRepository.create(reservation, auto_commit=False)
            ReservationTableRepository.create_bulk(
                reservation.id,
                [t.id for t in assignment],
                auto_commit=False,
            )
            ReservationRepository.commit()
        except Exception:
            ReservationRepository.rollback()
            raise

        logger.info("Guest reservation created: id=%s code=%s", reservation.id, code)
        return ReservationService._to_payload(reservation)

    @staticmethod
    def create_for_admin(
        restaurant_id: UUID,
        admin_user_id: UUID,
        party_size: int,
        on_date: date,
        time_slot: time,
        source: ReservationSource,
        guest_name: str | None = None,
        guest_phone: str | None = None,
        guest_email: str | None = None,
        user_id: UUID | None = None,
        notes: str | None = None,
    ) -> dict:
        from app.services.availability_service import AvailabilityService
        from app.services.business_hours_service import BusinessHoursService

        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")

        if source not in (ReservationSource.PHONE, ReservationSource.EVENT):
            raise ValidationError(
                "source must be PHONE or EVENT for admin-created reservations.",
                {"source": "Must be PHONE or EVENT"},
            )

        normalized_guest_name = guest_name.strip() if guest_name else None
        normalized_guest_phone = guest_phone.strip() if guest_phone else None
        normalized_guest_email = guest_email.strip() if guest_email else None

        has_user = user_id is not None
        has_guest = bool(normalized_guest_name)
        if has_user == has_guest:
            raise ValidationError(
                "Provide either userId or guestName, not both.",
                {"userId": "Mutually exclusive with guestName"},
            )

        if has_user and not UserRepository.get_by_id(user_id):
            raise NotFoundError(f"User with id={user_id} not found.")

        if not isinstance(party_size, int):
            raise ValidationError("partySize must be an integer.", {"partySize": "Invalid type"})
        if party_size < 1:
            raise ValidationError("partySize must be at least 1.", {"partySize": "Must be >= 1"})

        # Validate that restaurant is open on the requested date
        if not BusinessHoursService.is_open_on(restaurant_id, on_date):
            raise ValidationError(
                f"Restaurant is closed on {on_date.isoformat()}.",
                {"date": "Restaurant is closed"},
            )

        # Validate that time_slot is within operating hours
        time_ranges = BusinessHoursService.get_time_ranges(restaurant_id, on_date)
        if not time_ranges:
            raise ValidationError(
                f"No operating hours defined for {on_date.isoformat()}.",
                {"date": "No operating hours"},
            )
        matching_range = _matching_business_range(time_slot, time_ranges)
        if matching_range is None:
            raise ValidationError(
                f"Time slot {time_slot.isoformat()} is outside operating hours ({_format_business_ranges(time_ranges)}).",
                {"timeSlot": "Outside operating hours"},
            )

        assignment = AvailabilityService.find_table_assignment(
            restaurant_id,
            on_date,
            time_slot,
            party_size,
            lock_rows=True,
        )
        if assignment is None:
            raise ConflictError(
                "No tables available for the requested date, time, and party size.",
                {"timeSlot": "Not available"},
            )

        code = _generate_unique_confirmation_code()
        reservation = ReservationModel(
            restaurant_id=restaurant_id,
            user_id=user_id,
            guest_name=normalized_guest_name,
            guest_phone=normalized_guest_phone,
            guest_email=normalized_guest_email,
            party_size=party_size,
            date=on_date,
            time_slot=time_slot,
            source=source,
            status=ReservationStatus.CONFIRMED,
            notes=notes,
            confirmation_code=code,
        )
        try:
            ReservationRepository.create(reservation, auto_commit=False)
            ReservationTableRepository.create_bulk(
                reservation.id,
                [t.id for t in assignment],
                auto_commit=False,
            )
            ReservationRepository.commit()
        except Exception:
            ReservationRepository.rollback()
            raise
        logger.info(
            "Admin reservation created: id=%s code=%s admin=%s", reservation.id, code, admin_user_id
        )
        return ReservationService._to_payload(reservation)

    @staticmethod
    def get_by_id(
        reservation_id: UUID,
        requesting_user_id: UUID,
        restaurant_id: UUID | None = None,
    ) -> dict:
        reservation = ReservationRepository.get_by_id(reservation_id)
        if not reservation:
            raise NotFoundError(f"Reservation with id={reservation_id} not found.")
        if restaurant_id is not None and reservation.restaurant_id != restaurant_id:
            raise NotFoundError(
                f"Reservation with id={reservation_id} not found for restaurant id={restaurant_id}."
            )
        ReservationService._assert_can_access_reservation(
            reservation,
            requesting_user_id,
            message="You do not have access to this reservation.",
        )
        return ReservationService._to_payload(reservation)

    @staticmethod
    def get_by_confirmation_code(code: str) -> dict:
        reservation = ReservationRepository.get_by_code(code)
        if not reservation:
            raise NotFoundError(f"Reservation with confirmation code '{code}' not found.")
        return ReservationService._to_payload(reservation)

    @staticmethod
    def transition_status(
        reservation_id: UUID,
        requesting_user_id: UUID,
        status: str,
        reason: str | None = None,
    ) -> dict:
        try:
            target_status = ReservationStatus(str(status).upper())
        except (TypeError, ValueError) as error:
            raise ValidationError(
                "Invalid reservation status.",
                {"status": "Must be one of: CANCELLED, COMPLETED, NO_SHOW"},
            ) from error

        if target_status == ReservationStatus.CANCELLED:
            return ReservationService.cancel(
                reservation_id=reservation_id,
                requesting_user_id=requesting_user_id,
                reason=reason,
            )

        if target_status not in (
            ReservationStatus.COMPLETED,
            ReservationStatus.NO_SHOW,
        ):
            raise ValidationError(
                "Unsupported reservation status transition.",
                {"status": "Must be one of: CANCELLED, COMPLETED, NO_SHOW"},
            )

        reservation = ReservationRepository.get_by_id(reservation_id)
        if not reservation:
            raise NotFoundError(f"Reservation with id={reservation_id} not found.")
        if not ReservationService._is_restaurant_admin_or_super_admin(
            requesting_user_id,
            reservation.restaurant_id,
        ):
            raise ForbiddenError("Only restaurant admins can update reservation status.")

        if target_status == ReservationStatus.COMPLETED:
            return ReservationService.complete(reservation_id)
        return ReservationService.mark_no_show(reservation_id)

    @staticmethod
    def reassign_tables(
        reservation_id: UUID, table_ids: list[UUID], requesting_user_id: UUID
    ) -> dict:
        from app.repositories.table_repository import TableRepository

        reservation = ReservationRepository.get_by_id(reservation_id)
        if not reservation:
            raise NotFoundError(f"Reservation with id={reservation_id} not found.")
        from app.repositories.restaurant_admin_repository import RestaurantAdminRepository
        if not RestaurantAdminRepository.is_admin(
            user_id=requesting_user_id, restaurant_id=reservation.restaurant_id
        ):
            raise ForbiddenError("Only restaurant admins can reassign tables.")

        active_tables = TableRepository.get_active_for_update(reservation.restaurant_id)
        active_table_ids = {row.id for row in active_tables}
        invalid_table_ids = [tid for tid in table_ids if tid not in active_table_ids]
        if invalid_table_ids:
            raise ValidationError(
                "One or more tables are not active in this restaurant.",
                {"tableIds": "Invalid table ids"},
            )

        restaurant = RestaurantRepository.get_by_id(reservation.restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={reservation.restaurant_id} not found.")

        occupied = ReservationRepository.get_occupied_table_ids_at(
            reservation.restaurant_id,
            reservation.date,
            reservation.time_slot,
            exclude_reservation_id=reservation_id,
        )
        conflicts = [tid for tid in table_ids if tid in occupied]
        if conflicts:
            raise ConflictError(
                "One or more tables are already occupied at this time slot.",
                {"tableIds": "Conflict detected"},
            )

        try:
            ReservationTableRepository.delete_by_reservation(
                reservation_id,
                auto_commit=False,
            )
            ReservationTableRepository.create_bulk(
                reservation_id,
                table_ids,
                auto_commit=False,
            )
            ReservationRepository.commit()
        except Exception:
            ReservationRepository.rollback()
            raise
        logger.info("Reservation tables reassigned: id=%s", reservation_id)
        return ReservationService._to_payload(reservation)

    @staticmethod
    def cancel(
        reservation_id: UUID,
        requesting_user_id: UUID,
        reason: str | None = None,
        restaurant_id: UUID | None = None,
    ) -> dict:
        reservation = ReservationRepository.get_by_id(reservation_id)
        if not reservation:
            raise NotFoundError(f"Reservation with id={reservation_id} not found.")
        if restaurant_id and reservation.restaurant_id != restaurant_id:
            raise NotFoundError(
                f"Reservation with id={reservation_id} not found for restaurant id={restaurant_id}."
            )
        if reservation.status != ReservationStatus.CONFIRMED:
            if reservation.status == ReservationStatus.CANCELLED:
                raise ConflictError("Reservation is already cancelled.")
            raise ConflictError(
                f"Cannot cancel a reservation with status '{reservation.status.value}'."
            )
        ReservationService._assert_can_access_reservation(
            reservation,
            requesting_user_id,
            message="You do not have permission to cancel this reservation.",
        )

        ReservationRepository.cancel_and_release_tables(reservation)
        logger.info(
            "Reservation cancelled: id=%s by_user=%s reason=%s",
            reservation_id,
            requesting_user_id,
            reason,
        )
        return ReservationService._to_payload(reservation)

    @staticmethod
    def complete(reservation_id: UUID) -> dict:
        reservation = ReservationRepository.get_by_id(reservation_id)
        if not reservation:
            raise NotFoundError(f"Reservation with id={reservation_id} not found.")
        if reservation.status != ReservationStatus.CONFIRMED:
            raise ConflictError(
                f"Cannot complete a reservation with status '{reservation.status.value}'."
            )
        ReservationRepository.update_status(reservation, ReservationStatus.COMPLETED)
        logger.info("Reservation completed: id=%s", reservation_id)
        return ReservationService._to_payload(reservation)

    @staticmethod
    def mark_no_show(reservation_id: UUID) -> dict:
        reservation = ReservationRepository.get_by_id(reservation_id)
        if not reservation:
            raise NotFoundError(f"Reservation with id={reservation_id} not found.")
        if reservation.status != ReservationStatus.CONFIRMED:
            raise ConflictError(
                f"Cannot mark as no-show a reservation with status '{reservation.status.value}'."
            )
        ReservationRepository.mark_no_show_and_release_tables(reservation)
        logger.info("Reservation marked no-show: id=%s", reservation_id)
        return ReservationService._to_payload(reservation)
