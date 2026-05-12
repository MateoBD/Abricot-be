from uuid import UUID

from flask import request
from flask_restx import Namespace, Resource, reqparse

from app.api.auth.schemas import (
    auth_response_model,
    register_model,
    user_summary_model,
)
from app.api.users.schemas import (
    notification_preference_response_model,
    notification_preference_update_model,
    paginated_notification_preference_model,
    paginated_user_order_model,
    paginated_user_reservation_model,
    success_message_model,
    user_order_response_model,
    user_password_change_model,
    user_profile_response_model,
    user_profile_update_model,
    user_reservation_response_model,
    user_restaurant_response_model,
    user_restaurants_list_model,
)
from app.middleware.auth import (
    require_authentication,
    require_path_user_matches_jwt,
)
from app.services.auth_service import AuthService
from app.services.user_service import UserService

namespace = Namespace(
    name="Users",
    path="/users",
    description=(
        "User resources. User-id paths must match the JWT subject unless otherwise documented."
    ),
)

for _model in (
    register_model,
    user_summary_model,
    auth_response_model,
    user_profile_response_model,
    user_profile_update_model,
    user_password_change_model,
    success_message_model,
    user_reservation_response_model,
    paginated_user_reservation_model,
    user_order_response_model,
    paginated_user_order_model,
    user_restaurant_response_model,
    user_restaurants_list_model,
    notification_preference_response_model,
    notification_preference_update_model,
    paginated_notification_preference_model,
):
    namespace.models[_model.name] = _model

_pagination_parser = reqparse.RequestParser()
_pagination_parser.add_argument(
    "page",
    type=int,
    location="args",
    required=False,
    default=1,
    help="Page number (1-based).",
)
_pagination_parser.add_argument(
    "perPage",
    type=int,
    location="args",
    required=False,
    default=20,
    help="Items per page (max 100).",
)


@namespace.route("")
class UserCollection(Resource):
    @namespace.expect(register_model, validate=True)
    @namespace.response(201, "User registered successfully.", auth_response_model)
    @namespace.response(400, "Validation error.")
    @namespace.response(409, "Email already in use.")
    def post(self):
        """
        Create a user account.

        Returns both an access token (15 min) and a refresh token (30 days).
        """
        data = request.json
        return AuthService.register(
            email=data.get("email", ""),
            password=data.get("password", ""),
            name=data.get("name", ""),
            surname=data.get("surname", ""),
            role=data.get("role"),
        ), 201


@namespace.route("/<uuid:user_id>")
@namespace.doc(
    params={
        "user_id": "UUID of the user; must be the same as the authenticated user (JWT sub)."
    }
)
class UserProfile(Resource):
    @namespace.response(200, "User profile retrieved successfully.", user_profile_response_model)
    @namespace.response(403, "Forbidden; user id does not match the authenticated user.")
    @require_authentication()
    @require_path_user_matches_jwt("user_id")
    def get(self, user_id: UUID):
        """Get profile for the given user id (must equal JWT subject)."""
        return UserService.get_profile(user_id), 200

    @namespace.expect(user_profile_update_model, validate=True)
    @namespace.response(200, "User profile updated successfully.", user_profile_response_model)
    @namespace.response(400, "Validation error.")
    @namespace.response(403, "Forbidden; user id does not match the authenticated user.")
    @namespace.response(404, "User not found.")
    @require_authentication()
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
        "user_id": "UUID of the user; must be the same as the authenticated user (JWT sub)."
    }
)
class UserPassword(Resource):
    @namespace.expect(user_password_change_model, validate=True)
    @namespace.response(200, "Password changed successfully.", success_message_model)
    @namespace.response(400, "Validation error.")
    @namespace.response(401, "Current password is incorrect.")
    @namespace.response(403, "Forbidden; user id does not match the authenticated user.")
    @namespace.response(404, "User not found.")
    @require_authentication()
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


@namespace.route("/<uuid:user_id>/reservations")
@namespace.doc(params={"user_id": "UUID of the user; must match the authenticated user."})
class UserReservations(Resource):
    @namespace.expect(_pagination_parser)
    @namespace.response(200, "Reservations retrieved successfully.", paginated_user_reservation_model)
    @namespace.response(403, "Forbidden.")
    @namespace.response(404, "User not found.")
    @require_authentication()
    @require_path_user_matches_jwt("user_id")
    def get(self, user_id: UUID):
        """List reservations for the authenticated user."""
        args = _pagination_parser.parse_args()
        return UserService.get_my_reservations(
            user_id=user_id,
            page=args.get("page") or 1,
            per_page=args.get("perPage") or 20,
        ), 200


@namespace.route("/<uuid:user_id>/orders")
@namespace.doc(params={"user_id": "UUID of the user; must match the authenticated user."})
class UserOrders(Resource):
    @namespace.expect(_pagination_parser)
    @namespace.response(200, "Orders retrieved successfully.", paginated_user_order_model)
    @namespace.response(403, "Forbidden.")
    @namespace.response(404, "User not found.")
    @require_authentication()
    @require_path_user_matches_jwt("user_id")
    def get(self, user_id: UUID):
        """List orders for the authenticated user."""
        args = _pagination_parser.parse_args()
        return UserService.get_my_orders(
            user_id=user_id,
            page=args.get("page") or 1,
            per_page=args.get("perPage") or 20,
        ), 200


@namespace.route("/<uuid:user_id>/restaurants")
@namespace.doc(params={"user_id": "UUID of the user; must match the authenticated user."})
class UserRestaurants(Resource):
    @namespace.response(200, "Restaurants retrieved successfully.", user_restaurants_list_model)
    @namespace.response(403, "Forbidden.")
    @namespace.response(404, "User not found.")
    @require_authentication()
    @require_path_user_matches_jwt("user_id")
    def get(self, user_id: UUID):
        """List restaurants administered by the authenticated user."""
        return UserService.get_my_restaurants(user_id), 200


@namespace.route("/<uuid:user_id>/notification-preferences")
@namespace.doc(
    params={
        "user_id": "UUID of the user; must be the same as the authenticated user (JWT sub)."
    }
)
class UserNotificationPreferences(Resource):
    @namespace.expect(_pagination_parser)
    @namespace.response(
        200,
        "Notification preferences retrieved successfully.",
        paginated_notification_preference_model,
    )
    @namespace.response(403, "Forbidden; user id does not match the authenticated user.")
    @namespace.response(404, "User not found.")
    @require_authentication()
    @require_path_user_matches_jwt("user_id")
    def get(self, user_id: UUID):
        """Get all notification preferences for the authenticated user."""
        from app.services.notification_preference_service import (
            NotificationPreferenceService,
        )

        _pagination_parser.parse_args()
        result = NotificationPreferenceService.get_all_for_user(user_id)
        return result, 200


@namespace.route("/<uuid:user_id>/notification-preferences/<uuid:restaurant_id>")
@namespace.doc(
    params={
        "user_id": "UUID of the user; must be the same as the authenticated user (JWT sub).",
        "restaurant_id": "UUID of the restaurant.",
    }
)
class UserNotificationPreferenceDetail(Resource):
    @namespace.response(
        200,
        "Notification preference retrieved successfully.",
        notification_preference_response_model,
    )
    @namespace.response(403, "Forbidden; user id does not match the authenticated user.")
    @namespace.response(404, "User or restaurant not found.")
    @require_authentication()
    @require_path_user_matches_jwt("user_id")
    def get(self, user_id: UUID, restaurant_id: UUID):
        """Get notification preference for a specific restaurant."""
        from app.services.notification_preference_service import (
            NotificationPreferenceService,
        )

        return NotificationPreferenceService.get_or_create(user_id, restaurant_id), 200

    @namespace.expect(notification_preference_update_model, validate=True)
    @namespace.response(
        200,
        "Notification preference updated successfully.",
        notification_preference_response_model,
    )
    @namespace.response(400, "Validation error.")
    @namespace.response(403, "Forbidden; user id does not match the authenticated user.")
    @namespace.response(404, "User or restaurant not found.")
    @require_authentication()
    @require_path_user_matches_jwt("user_id")
    def put(self, user_id: UUID, restaurant_id: UUID):
        """Update notification preferences for a specific restaurant."""
        from app.services.notification_preference_service import (
            NotificationPreferenceService,
        )

        data = request.json
        return NotificationPreferenceService.update(
            user_id=user_id,
            restaurant_id=restaurant_id,
            receive_promotions=data.get("receivePromotions"),
            receive_order_updates=data.get("receiveOrderUpdates"),
            receive_reservation_reminders=data.get("receiveReservationReminders"),
        ), 200
