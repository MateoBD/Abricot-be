from uuid import UUID

from flask_restx import Namespace, Resource

from app.api.restaurants.schemas import reservation_response_model
from app.middleware.auth import get_current_user_id, require_authentication
from app.services.reservation_service import ReservationService

namespace = Namespace(
    name="Reservations",
    path="/reservations",
    description="Reservation lifecycle endpoints.",
    decorators=[require_authentication()],
)

namespace.models[reservation_response_model.name] = reservation_response_model


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
        return ReservationService.complete(
            reservation_id=reservation_id,
            requesting_user_id=get_current_user_id(),
        ), 200


@namespace.route("/<uuid:reservation_id>/no-show")
@namespace.doc(params={"reservation_id": "The reservation's ID (UUID)."})
class ReservationNoShow(Resource):
    @namespace.response(200, "Reservation marked no-show successfully.", reservation_response_model)
    @namespace.response(403, "Forbidden.")
    @namespace.response(404, "Reservation not found.")
    @namespace.response(409, "Reservation cannot be marked no-show in current status.")
    def patch(self, reservation_id: UUID):
        """Mark a confirmed reservation as no-show and release assigned tables."""
        return ReservationService.mark_no_show(
            reservation_id=reservation_id,
            requesting_user_id=get_current_user_id(),
        ), 200
