from uuid import UUID

from flask_restx import Namespace, Resource

from app.api.restaurants.schemas import reservation_response_model
from app.exceptions.errors import ForbiddenError, NotFoundError
from app.middleware.auth import get_current_user_id, require_authentication
from app.models.enums import UserRole
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.restaurant_admin_repository import RestaurantAdminRepository
from app.repositories.user_repository import UserRepository
from app.services.reservation_service import ReservationService

namespace = Namespace(
    name="Reservations",
    path="/reservations",
    description="Reservation lifecycle endpoints.",
    decorators=[require_authentication()],
)

namespace.models[reservation_response_model.name] = reservation_response_model


def _ensure_requester_is_restaurant_admin(reservation_id: UUID, requesting_user_id: UUID) -> None:
    reservation = ReservationRepository.get_by_id(reservation_id)
    if not reservation:
        raise NotFoundError(f"Reservation with id={reservation_id} not found.")

    user = UserRepository.get_by_id(requesting_user_id)
    if not user:
        raise ForbiddenError("You do not have permission to perform this action.")

    if user.role == UserRole.SUPER_ADMIN:
        return

    if user.role != UserRole.RESTAURANT_ADMIN:
        raise ForbiddenError("Only restaurant admins can update reservation status.")

    if not RestaurantAdminRepository.is_admin(
        user_id=requesting_user_id,
        restaurant_id=reservation.restaurant_id,
    ):
        raise ForbiddenError("Only restaurant admins can update reservation status.")


@namespace.route("/<uuid:reservation_id>")
@namespace.doc(params={"reservation_id": "The reservation's ID (UUID)."})
class ReservationDetail(Resource):
    @namespace.response(200, "Reservation retrieved successfully.", reservation_response_model)
    @namespace.response(401, "Unauthorized.")
    @namespace.response(403, "Forbidden.")
    @namespace.response(404, "Reservation not found.")
    def get(self, reservation_id: UUID):
        """Get a reservation by id (owner or restaurant admin only)."""
        return ReservationService.get_by_id(
            reservation_id=reservation_id,
            requesting_user_id=get_current_user_id(),
        ), 200


@namespace.route("/<uuid:reservation_id>/complete")
@namespace.doc(params={"reservation_id": "The reservation's ID (UUID)."})
class ReservationComplete(Resource):
    @namespace.response(200, "Reservation completed successfully.", reservation_response_model)
    @namespace.response(403, "Forbidden.")
    @namespace.response(404, "Reservation not found.")
    @namespace.response(409, "Reservation cannot be completed in current status.")
    def patch(self, reservation_id: UUID):
        """Mark a confirmed reservation as completed (restaurant admin only)."""
        _ensure_requester_is_restaurant_admin(reservation_id, get_current_user_id())
        return ReservationService.complete(reservation_id), 200


@namespace.route("/<uuid:reservation_id>/no-show")
@namespace.doc(params={"reservation_id": "The reservation's ID (UUID)."})
class ReservationNoShow(Resource):
    @namespace.response(200, "Reservation marked no-show successfully.", reservation_response_model)
    @namespace.response(403, "Forbidden.")
    @namespace.response(404, "Reservation not found.")
    @namespace.response(409, "Reservation cannot be marked no-show in current status.")
    def patch(self, reservation_id: UUID):
        """Mark a confirmed reservation as no-show and release assigned tables."""
        _ensure_requester_is_restaurant_admin(reservation_id, get_current_user_id())
        return ReservationService.mark_no_show(reservation_id), 200
