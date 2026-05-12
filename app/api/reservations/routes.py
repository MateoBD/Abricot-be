from uuid import UUID

from flask import request
from flask_restx import Namespace, Resource

from app.api.restaurants.schemas import (
    reservation_response_model,
    reservation_status_patch_model,
)
from app.middleware.auth import get_current_user_id, require_authentication
from app.services.reservation_service import ReservationService

namespace = Namespace(
    name="Reservations",
    path="/reservations",
    description="Reservation resources and lifecycle state updates.",
    decorators=[require_authentication()],
)

for _model in (reservation_response_model, reservation_status_patch_model):
    namespace.models[_model.name] = _model


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

    @namespace.expect(reservation_status_patch_model, validate=True)
    @namespace.response(200, "Reservation status updated successfully.", reservation_response_model)
    @namespace.response(400, "Validation error.")
    @namespace.response(403, "Forbidden.")
    @namespace.response(404, "Reservation not found.")
    @namespace.response(409, "Reservation cannot transition to the requested status.")
    def patch(self, reservation_id: UUID):
        """Update reservation lifecycle state."""
        data = request.json or {}
        return ReservationService.transition_status(
            reservation_id=reservation_id,
            requesting_user_id=get_current_user_id(),
            status=data.get("status"),
            reason=data.get("reason"),
        ), 200
