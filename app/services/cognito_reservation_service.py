import logging
from uuid import UUID

from app.exceptions.errors import ForbiddenError, ValidationError
from app.models.enums import UserSnsSubscriptionStatus
from app.services.cognito_authorization_service import CognitoAuthorizationService
from app.services.reservation_service import ReservationService
from app.services.sns_user_notification_service import SnsUserNotificationService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


def _parse_uuid(value: str | UUID | None, field: str) -> UUID:
    if value is None or value == "":
        raise ValidationError(f"{field} is required.", {field: "Required"})
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError as error:
        raise ValidationError("Invalid identifier format.", {field: "Invalid UUID"}) from error


_BODY_ALIASES = {
    "partySize": ("partySize", "party_size"),
    "date": ("date", "reservationDate", "reservation_date"),
    "timeSlot": ("timeSlot", "time", "reservationTime", "reservation_time"),
    "notes": ("notes", "specialRequests", "special_requests"),
    "guestName": ("guestName", "customerName", "guest_name", "customer_name"),
    "guestEmail": ("guestEmail", "customerEmail", "guest_email", "customer_email"),
    "guestPhone": ("guestPhone", "customerPhone", "guest_phone", "customer_phone"),
    "userId": ("userId", "user_id"),
}


def _first_present(body: dict, names: tuple[str, ...]):
    for name in names:
        if name in body and body.get(name) not in (None, ""):
            return body.get(name)
    return None


def _normalized_body(body: dict | None) -> dict:
    normalized = dict(body or {})
    for target, aliases in _BODY_ALIASES.items():
        value = _first_present(normalized, aliases)
        if value is not None:
            normalized[target] = value
    return normalized


def _parse_party_size(value) -> int:
    if isinstance(value, bool):
        raise ValidationError("partySize must be an integer.", {"partySize": "Invalid type"})
    try:
        party_size = int(value)
    except (TypeError, ValueError) as error:
        raise ValidationError("partySize must be an integer.", {"partySize": "Invalid type"}) from error
    if party_size < 1:
        raise ValidationError("partySize must be at least 1.", {"partySize": "Must be >= 1"})
    return party_size


class CognitoReservationService:
    @staticmethod
    def create(
        *,
        restaurant_id: str | UUID,
        cognito_sub: str | None,
        body: dict,
        is_cognito_admin: bool = False,
    ) -> dict:
        body = _normalized_body(body)
        restaurant_uuid = _parse_uuid(restaurant_id, "restaurantId")
        principal = CognitoAuthorizationService.principal_user(cognito_sub)
        source = str(body.get("source") or "ONLINE").upper()

        if source in ("PHONE", "EVENT"):
            CognitoAuthorizationService.reject_privilege_fields(body, allow_user_id=True)
            CognitoAuthorizationService.require_restaurant_admin(
                principal=principal,
                restaurant_id=restaurant_uuid,
                is_cognito_admin=is_cognito_admin,
            )
            user_id = body.get("userId")
            return ReservationService.create_for_admin(
                restaurant_id=restaurant_uuid,
                admin_user_id=principal.id,
                party_size=_parse_party_size(body.get("partySize")),
                on_date=ReservationService.parse_required_date(body.get("date")),
                time_slot=ReservationService.parse_required_time(body.get("timeSlot")),
                source=ReservationService.parse_required_admin_source(source),
                guest_name=body.get("guestName"),
                guest_phone=body.get("guestPhone"),
                guest_email=body.get("guestEmail"),
                user_id=_parse_uuid(user_id, "userId") if user_id is not None else None,
                notes=body.get("notes"),
            )

        if source != "ONLINE":
            raise ValidationError(
                "Invalid source.",
                {"source": "Must be one of: ONLINE, PHONE, EVENT"},
            )

        CognitoAuthorizationService.reject_privilege_fields(body)
        principal = SnsUserNotificationService.refresh_subscription_status(principal)
        if principal.sns_subscription_status != UserSnsSubscriptionStatus.CONFIRMED:
            raise ForbiddenError(
                "User email SNS subscription is not confirmed.",
                {"snsSubscriptionStatus": principal.sns_subscription_status.value if principal.sns_subscription_status else None},
                public_message="Confirma la suscripcion de email antes de reservar.",
            )

        reservation = ReservationService.create(
            restaurant_id=restaurant_uuid,
            user_id=principal.id,
            party_size=_parse_party_size(body.get("partySize")),
            on_date=ReservationService.parse_required_date(body.get("date")),
            time_slot=ReservationService.parse_required_time(body.get("timeSlot")),
            notes=body.get("notes"),
        )
        try:
            SnsUserNotificationService.publish_reservation_confirmation(
                _parse_uuid(reservation.get("id"), "reservationId")
            )
        except Exception:
            logger.exception(
                "reservation_sns_confirmation_publish_failed",
                extra={"reservation_id": reservation.get("id")},
            )
        return reservation

    @staticmethod
    def create_public(*, restaurant_id: str | UUID, body: dict) -> dict:
        body = _normalized_body(body)
        return ReservationService.create_guest_online(
            restaurant_id=_parse_uuid(restaurant_id, "restaurantId"),
            party_size=_parse_party_size(body.get("partySize")),
            on_date=ReservationService.parse_required_date(body.get("date")),
            time_slot=ReservationService.parse_required_time(body.get("timeSlot")),
            guest_name=body.get("guestName"),
            guest_phone=body.get("guestPhone"),
            guest_email=body.get("guestEmail"),
            notes=body.get("notes"),
        )

    @staticmethod
    def list_for_restaurant(
        *,
        restaurant_id: str | UUID,
        cognito_sub: str | None,
        query: dict[str, str],
        is_cognito_admin: bool = False,
    ) -> dict:
        restaurant_uuid = _parse_uuid(restaurant_id, "restaurantId")
        principal = CognitoAuthorizationService.principal_user(cognito_sub)
        CognitoAuthorizationService.require_restaurant_admin(
            principal=principal,
            restaurant_id=restaurant_uuid,
            is_cognito_admin=is_cognito_admin,
        )
        return ReservationService.list_for_restaurant(
            restaurant_id=restaurant_uuid,
            on_date=query.get("date"),
            status=query.get("status"),
            source=query.get("source"),
            page=_int_query(query, "page", 1),
            per_page=_int_query(query, "perPage", 20),
        )

    @staticmethod
    def list_for_user(
        *,
        user_id: str | UUID,
        cognito_sub: str | None,
        query: dict[str, str],
        is_cognito_admin: bool = False,
    ) -> dict:
        target_user_id = _parse_uuid(user_id, "userId")
        principal = CognitoAuthorizationService.principal_user(cognito_sub)
        CognitoAuthorizationService.require_same_user_or_super_admin(
            principal=principal,
            target_user_id=target_user_id,
            is_cognito_admin=is_cognito_admin,
        )
        return UserService.get_my_reservations(
            target_user_id,
            page=_int_query(query, "page", 1),
            per_page=_int_query(query, "perPage", 20),
        )

    @staticmethod
    def get_by_id(
        *,
        reservation_id: str | UUID,
        cognito_sub: str | None,
    ) -> dict:
        principal = CognitoAuthorizationService.principal_user(cognito_sub)
        return ReservationService.get_by_id(
            reservation_id=_parse_uuid(reservation_id, "reservationId"),
            requesting_user_id=principal.id,
        )

    @staticmethod
    def transition_status(
        *,
        reservation_id: str | UUID,
        cognito_sub: str | None,
        body: dict,
    ) -> dict:
        principal = CognitoAuthorizationService.principal_user(cognito_sub)
        return ReservationService.transition_status(
            reservation_id=_parse_uuid(reservation_id, "reservationId"),
            requesting_user_id=principal.id,
            status=body.get("status"),
            reason=body.get("reason"),
        )


def _int_query(query: dict[str, str], name: str, default: int) -> int:
    try:
        return int(query.get(name, str(default)))
    except ValueError:
        return default
