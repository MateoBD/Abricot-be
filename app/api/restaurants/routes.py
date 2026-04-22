from flask import request
from flask_restx import Namespace, Resource, reqparse
from werkzeug.datastructures import FileStorage

from app.api.restaurants.schemas import (
    paginated_restaurant_admin_response_model,
    paginated_restaurant_response_model,
    general_metrics_response_model,
    orders_report_response_model,
    restaurant_admin_add_model,
    restaurant_admin_response_model,
    restaurant_create_model,
    restaurant_response_model,
    restaurant_update_model,
)
from app.middleware.auth import (
    get_current_user_id,
    require_authentication,
    require_restaurant_admin,
    require_roles,
)
from app.models.enums import UserRole
from app.services.restaurant_service import RestaurantService
from app.services.analytics_service import AnalyticsService
from app.services.restaurant_admin_service import RestaurantAdminService

namespace = Namespace(
    name="Restaurants",
    path="/restaurants",
    description="ABM de restaurantes.",
    decorators=[require_authentication()],
)

for _model in (
    restaurant_create_model,
    restaurant_update_model,
    paginated_restaurant_response_model,
    paginated_restaurant_admin_response_model,
    restaurant_response_model,
    restaurant_admin_add_model,
    restaurant_admin_response_model,
    orders_report_response_model,
    general_metrics_response_model,
):
    namespace.models[_model.name] = _model

_photo_parser = reqparse.RequestParser()
_photo_parser.add_argument(
    "file",
    type=FileStorage,
    location="files",
    required=True,
    help="Image file to upload.",
)

_analytics_date_range_parser = reqparse.RequestParser()
_analytics_date_range_parser.add_argument(
    "start",
    type=str,
    location="args",
    required=True,
    help="Start date in YYYY-MM-DD format.",
)
_analytics_date_range_parser.add_argument(
    "end",
    type=str,
    location="args",
    required=True,
    help="End date in YYYY-MM-DD format.",
)


@namespace.route("/")
class RestaurantList(Resource):
    """Endpoints for listing and creating restaurants."""

    @namespace.response(200, "Restaurants retrieved successfully.", paginated_restaurant_response_model)
    def get(self):
        """List all restaurants ordered alphabetically by name."""
        return RestaurantService.get_all(), 200

    @namespace.expect(restaurant_create_model, validate=True)
    @namespace.response(201, "Restaurant created successfully.", restaurant_response_model)
    @namespace.response(400, "Validation error.")
    @require_roles(UserRole.RESTAURANT_ADMIN, UserRole.SUPER_ADMIN)
    def post(self):
        """Create a new restaurant."""
        data = request.json
        return RestaurantService.create(
            name=data.get("name", ""),
            address=data.get("address", ""),
            phone=data.get("phone", ""),
            email=data.get("email"),
            description=data.get("description"),
            creator_user_id=get_current_user_id(),
        ), 201


@namespace.route("/<int:restaurant_id>")
@namespace.doc(params={"restaurant_id": "The restaurant's ID."})
class RestaurantDetail(Resource):
    """Endpoints for retrieving, updating, and deleting a single restaurant."""

    @namespace.response(200, "Restaurant retrieved successfully.", restaurant_response_model)
    @namespace.response(404, "Restaurant not found.")
    def get(self, restaurant_id: int):
        """Get a restaurant by ID."""
        return RestaurantService.get_by_id(restaurant_id), 200

    @namespace.expect(restaurant_update_model, validate=True)
    @namespace.response(200, "Restaurant updated successfully.", restaurant_response_model)
    @namespace.response(404, "Restaurant not found.")
    @require_restaurant_admin("restaurant_id")
    def put(self, restaurant_id: int):
        """Replace all fields of a restaurant. Omitting optional fields clears them."""
        data = request.json
        return RestaurantService.update(
            restaurant_id=restaurant_id,
            name=data.get("name", ""),
            address=data.get("address", ""),
            phone=data.get("phone", ""),
            email=data.get("email"),
            description=data.get("description"),
        ), 200

    @namespace.response(204, "Restaurant deleted successfully.")
    @namespace.response(404, "Restaurant not found.")
    @require_restaurant_admin("restaurant_id")
    def delete(self, restaurant_id: int):
        """Delete a restaurant by ID."""
        RestaurantService.delete(restaurant_id)
        return "", 204


@namespace.route("/<int:restaurant_id>/photo")
@namespace.doc(params={"restaurant_id": "The restaurant's ID."})
class RestaurantPhoto(Resource):
    """Endpoint for uploading a restaurant's photo to S3."""

    @namespace.expect(_photo_parser)
    @namespace.response(200, "Photo uploaded successfully.", restaurant_response_model)
    @namespace.response(400, "No file provided.")
    @namespace.response(404, "Restaurant not found.")
    @require_restaurant_admin("restaurant_id")
    def post(self, restaurant_id: int):
        """Upload a photo for a restaurant via multipart/form-data."""
        args = _photo_parser.parse_args()
        file = args["file"]
        return RestaurantService.upload_photo(restaurant_id, file), 200


@namespace.route("/<int:restaurant_id>/admins")
@namespace.doc(params={"restaurant_id": "The restaurant's ID."})
class RestaurantAdmins(Resource):
    @namespace.response(200, "Restaurant admins retrieved successfully.", paginated_restaurant_admin_response_model)
    @namespace.response(404, "Restaurant not found.")
    @require_restaurant_admin("restaurant_id")
    def get(self, restaurant_id: int):
        """List all administrators assigned to a restaurant."""
        return RestaurantAdminService.list_admins(restaurant_id), 200

    @namespace.expect(restaurant_admin_add_model, validate=True)
    @namespace.response(201, "Restaurant admin added successfully.", restaurant_admin_response_model)
    @namespace.response(404, "Restaurant or user not found.")
    @namespace.response(409, "User is already an admin for this restaurant.")
    @require_restaurant_admin("restaurant_id")
    def post(self, restaurant_id: int):
        """Assign a user as administrator of a restaurant."""
        data = request.json
        return RestaurantAdminService.add_admin(
            restaurant_id=restaurant_id,
            user_id=data.get("userId"),
        ), 201


@namespace.route("/<int:restaurant_id>/admins/<int:user_id>")
@namespace.doc(
    params={
        "restaurant_id": "The restaurant's ID.",
        "user_id": "The user ID to remove as restaurant admin.",
    }
)
class RestaurantAdminDetail(Resource):
    @namespace.response(204, "Restaurant admin removed successfully.")
    @namespace.response(404, "Restaurant, user, or admin relation not found.")
    @require_restaurant_admin("restaurant_id")
    def delete(self, restaurant_id: int, user_id: int):
        """Remove a user from the administrators of a restaurant."""
        RestaurantAdminService.remove_admin(restaurant_id=restaurant_id, user_id=user_id)
        return "", 204


@namespace.route("/<int:restaurant_id>/analytics/orders")
@namespace.doc(params={"restaurant_id": "The restaurant's ID."})
class RestaurantOrdersReport(Resource):
    @namespace.response(
        200,
        "Orders analytics retrieved successfully.",
        orders_report_response_model,
    )
    @namespace.response(400, "Validation error.")
    @namespace.response(404, "Restaurant not found.")
    @namespace.expect(_analytics_date_range_parser)
    @require_restaurant_admin("restaurant_id")
    def get(self, restaurant_id: int):
        """Get orders analytics report for a restaurant within a date range."""
        args = _analytics_date_range_parser.parse_args()
        return AnalyticsService.get_orders_report(
            restaurant_id=restaurant_id,
            start=args.get("start"),
            end=args.get("end"),
        ), 200

@namespace.route("/<int:restaurant_id>/analytics/metrics")
@namespace.doc(params={"restaurant_id": "The restaurant's ID."})
class RestaurantGeneralMetrics(Resource):
    @namespace.response(
        200,
        "General metrics retrieved successfully.",
        general_metrics_response_model,
    )
    @namespace.response(400, "Validation error.")
    @namespace.response(404, "Restaurant not found.")
    @namespace.expect(_analytics_date_range_parser)
    @require_restaurant_admin("restaurant_id")
    def get(self, restaurant_id: int):
        """Get general metrics for a restaurant (orders, reservations, revenue) within a date range."""
        args = _analytics_date_range_parser.parse_args()
        return AnalyticsService.get_general_metrics(
            restaurant_id=restaurant_id,
            start=args.get("start"),
            end=args.get("end"),
        ), 200