from datetime import date
import logging
from uuid import UUID

from app.exceptions.errors import NotFoundError, ValidationError
from app.models.enums import ReservationSource, ReservationStatus
from app.models.reservation import ReservationModel
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.utils.list_envelope import paginated_list_envelope

logger = logging.getLogger(__name__)


class ReservationService:
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
