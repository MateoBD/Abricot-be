from flask import request
from flask_restx import Namespace, Resource

from app.api.users.schemas import (
    success_message_model,
    user_password_change_model,
    user_profile_response_model,
    user_profile_update_model,
)
from app.middleware.auth import get_current_user_id, require_authentication
from app.services.user_service import UserService

namespace = Namespace(
    name="Users",
    path="/users",
    description="Authenticated user profile endpoints.",
    decorators=[require_authentication()],
)

for _model in (
    user_profile_response_model,
    user_profile_update_model,
    user_password_change_model,
    success_message_model,
):
    namespace.models[_model.name] = _model


@namespace.route("/me")
class UserProfile(Resource):
    @namespace.response(200, "User profile retrieved successfully.", user_profile_response_model)
    def get(self):
        """Get profile for the authenticated user."""
        return UserService.get_profile(get_current_user_id()), 200

    @namespace.expect(user_profile_update_model, validate=True)
    @namespace.response(200, "User profile updated successfully.", user_profile_response_model)
    @namespace.response(400, "Validation error.")
    @namespace.response(404, "User not found.")
    def put(self):
        """Update basic profile fields for the authenticated user."""
        data = request.json
        return UserService.update_profile(
            user_id=get_current_user_id(),
            name=data.get("name", ""),
            surname=data.get("surname", ""),
        ), 200


@namespace.route("/me/password")
class UserPassword(Resource):
    @namespace.expect(user_password_change_model, validate=True)
    @namespace.response(200, "Password changed successfully.", success_message_model)
    @namespace.response(400, "Validation error.")
    @namespace.response(401, "Current password is incorrect.")
    @namespace.response(404, "User not found.")
    def put(self):
        """Change password for the authenticated user."""
        data = request.json
        UserService.change_password(
            user_id=get_current_user_id(),
            current_password=data.get("currentPassword", ""),
            new_password=data.get("newPassword", ""),
        )
        return {"message": "Password updated successfully."}, 200
