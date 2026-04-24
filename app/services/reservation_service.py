import random
import string
from datetime import date, time
import logging
from uuid import UUID

from app.exceptions.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.enums import ReservationSource, ReservationStatus
from app.models.reservation import ReservationModel
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.reservation_table_repository import ReservationTableRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.user_repository import UserRepository
from app.utils.list_envelope import paginated_list_envelope

logger = logging.getLogger(__name__)


def _generate_confirmation_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


class ReservationService:
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

        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        if not isinstance(party_size, int):
            raise ValidationError("partySize must be an integer.", {"partySize": "Invalid type"})
        if party_size < 1:
            raise ValidationError("partySize must be at least 1.", {"partySize": "Must be >= 1"})

        assignment = AvailabilityService.find_table_assignment(
            restaurant_id, on_date, time_slot, party_size
        )
        if assignment is None:
            raise ConflictError(
                "No tables available for the requested date, time, and party size.",
                {"timeSlot": "Not available"},
            )

        code = _generate_confirmation_code()
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
        ReservationRepository.create(reservation)
        ReservationTableRepository.create_bulk(reservation.id, [t.id for t in assignment])
        logger.info("Reservation created: id=%s code=%s", reservation.id, code)
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

        assignment = AvailabilityService.find_table_assignment(
            restaurant_id, on_date, time_slot, party_size
        )
        if assignment is None:
            raise ConflictError(
                "No tables available for the requested date, time, and party size.",
                {"timeSlot": "Not available"},
            )

        code = _generate_confirmation_code()
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
        ReservationRepository.create(reservation)
        ReservationTableRepository.create_bulk(reservation.id, [t.id for t in assignment])
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
        if reservation.user_id != requesting_user_id:
            from app.repositories.restaurant_admin_repository import RestaurantAdminRepository
            is_admin = RestaurantAdminRepository.is_admin(
                user_id=requesting_user_id, restaurant_id=reservation.restaurant_id
            )
            if not is_admin:
                raise ForbiddenError("You do not have access to this reservation.")
        return ReservationService._to_payload(reservation)

    @staticmethod
    def get_by_confirmation_code(code: str) -> dict:
        reservation = ReservationRepository.get_by_code(code)
        if not reservation:
            raise NotFoundError(f"Reservation with confirmation code '{code}' not found.")
        return ReservationService._to_payload(reservation)

    @staticmethod
    def reassign_tables(
        reservation_id: UUID, table_ids: list[UUID], requesting_user_id: UUID
    ) -> dict:
        reservation = ReservationRepository.get_by_id(reservation_id)
        if not reservation:
            raise NotFoundError(f"Reservation with id={reservation_id} not found.")
        from app.repositories.restaurant_admin_repository import RestaurantAdminRepository
        if not RestaurantAdminRepository.is_admin(
            user_id=requesting_user_id, restaurant_id=reservation.restaurant_id
        ):
            raise ForbiddenError("Only restaurant admins can reassign tables.")

        occupied = ReservationRepository.get_occupied_table_ids_at(
            reservation.restaurant_id, reservation.date, reservation.time_slot
        )
        conflicts = [tid for tid in table_ids if tid in occupied]
        if conflicts:
            raise ConflictError(
                "One or more tables are already occupied at this time slot.",
                {"tableIds": "Conflict detected"},
            )

        ReservationTableRepository.delete_by_reservation(reservation_id)
        ReservationTableRepository.create_bulk(reservation_id, table_ids)
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
        if reservation.user_id != requesting_user_id:
            from app.repositories.restaurant_admin_repository import RestaurantAdminRepository
            if not RestaurantAdminRepository.is_admin(
                user_id=requesting_user_id, restaurant_id=reservation.restaurant_id
            ):
                raise ForbiddenError("You do not have permission to cancel this reservation.")

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
        ReservationRepository.update_status(reservation, ReservationStatus.NO_SHOW)
        logger.info("Reservation marked no-show: id=%s", reservation_id)
        return ReservationService._to_payload(reservation)
