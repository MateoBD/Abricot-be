from uuid import UUID

from flask import request
from flask_restx import Namespace, Resource

from app.api.users.schemas import (
    success_message_model,
    user_password_change_model,
    user_profile_response_model,
    user_profile_update_model,
)
from app.middleware.auth import (
    require_authentication,
    require_path_user_matches_jwt,
)
from app.services.user_service import UserService

namespace = Namespace(
    name="Users",
    path="/users",
    description=(
        "User profile by resource id. Path `user_id` must match the JWT subject."
    ),
    decorators=[require_authentication()],
)

for _model in (
    user_profile_response_model,
    user_profile_update_model,
    user_password_change_model,
    success_message_model,
):
    namespace.models[_model.name] = _model


@namespace.route("/<uuid:user_id>")
@namespace.doc(
    params={
        "user_id": "UUID of the user — must be the same as the authenticated user (JWT `sub`)."
    }
)
class UserProfile(Resource):
    @namespace.response(200, "User profile retrieved successfully.", user_profile_response_model)
    @namespace.response(403, "Forbidden — user id does not match the authenticated user.")
    @require_path_user_matches_jwt("user_id")
    def get(self, user_id: UUID):
        """Get profile for the given user id (must equal JWT subject)."""
        return UserService.get_profile(user_id), 200

    @namespace.expect(user_profile_update_model, validate=True)
    @namespace.response(200, "User profile updated successfully.", user_profile_response_model)
    @namespace.response(400, "Validation error.")
    @namespace.response(403, "Forbidden — user id does not match the authenticated user.")
    @namespace.response(404, "User not found.")
    @require_path_user_matches_jwt("user_id")
    def put(self, user_id: UUID):
        """Update basic profile fields for the given user id (must equal JWT subject)."""
        data = request.json
        return UserService.update_profile(
            user_id=user_id,
            name=data.get("name", ""),
            surname=data.get("surname", ""),
        ), 200


@namespace.route("/<uuid:user_id>/password")
@namespace.doc(
    params={
        "user_id": "UUID of the user — must be the same as the authenticated user (JWT `sub`)."
    }
)
class UserPassword(Resource):
    @namespace.expect(user_password_change_model, validate=True)
    @namespace.response(200, "Password changed successfully.", success_message_model)
    @namespace.response(400, "Validation error.")
    @namespace.response(401, "Current password is incorrect.")
    @namespace.response(403, "Forbidden — user id does not match the authenticated user.")
    @namespace.response(404, "User not found.")
    @require_path_user_matches_jwt("user_id")
    def put(self, user_id: UUID):
        """Change password for the given user id (must equal JWT subject)."""
        data = request.json
        UserService.change_password(
            user_id=user_id,
            current_password=data.get("currentPassword", ""),
            new_password=data.get("newPassword", ""),
        )
        return {"message": "Password updated successfully."}, 200
