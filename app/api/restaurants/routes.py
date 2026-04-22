from uuid import UUID

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
from app.services.restaurant_service import FIELD_UNSET, RestaurantService
from app.services.analytics_service import AnalyticsService
from app.services.restaurant_admin_service import RestaurantAdminService

def _cuisine_type_ids_from_query() -> list[str] | None:
    raw = request.args.getlist("cuisineTypeIds")
    out: list[str] = []
    for part in raw:
        for bit in part.split(","):
            b = bit.strip()
            if b:
                out.append(b)
    return out or None


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
        """Search restaurants with optional filters and pagination."""
        q = request.args
        try:
            page = int(q.get("page", 1))
            per_page = int(q.get("perPage", 20))
        except ValueError:
            page, per_page = 1, 20
        return RestaurantService.search(
            name=q.get("name"),
            country_id=q.get("countryId"),
            province_id=q.get("provinceId"),
            city_id=q.get("cityId"),
            neighbourhood_id=q.get("neighbourhoodId"),
            price_range_id=q.get("priceRangeId"),
            cuisine_type_ids=_cuisine_type_ids_from_query(),
            page=page,
            per_page=per_page,
        ), 200

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
            city_id=data.get("cityId"),
            email=data.get("email"),
            description=data.get("description"),
            neighbourhood_id=data.get("neighbourhoodId"),
            price_range_id=data.get("priceRangeId"),
            cuisine_type_ids=data.get("cuisineTypeIds"),
            creator_user_id=get_current_user_id(),
        ), 201


@namespace.route("/<uuid:restaurant_id>")
@namespace.doc(params={"restaurant_id": "The restaurant's ID (UUID)."})
class RestaurantDetail(Resource):
    """Endpoints for retrieving, updating, and deleting a single restaurant."""

    @namespace.response(200, "Restaurant retrieved successfully.", restaurant_response_model)
    @namespace.response(404, "Restaurant not found.")
    def get(self, restaurant_id: UUID):
        """Get a restaurant by ID."""
        return RestaurantService.get_by_id(restaurant_id), 200

    @namespace.expect(restaurant_update_model, validate=True)
    @namespace.response(200, "Restaurant updated successfully.", restaurant_response_model)
    @namespace.response(404, "Restaurant not found.")
    @require_restaurant_admin("restaurant_id")
    def put(self, restaurant_id: UUID):
        """Replace all fields of a restaurant. Omitting optional fields clears them."""
        data = request.json
        return RestaurantService.update(
            restaurant_id=restaurant_id,
            name=data.get("name", ""),
            address=data.get("address", ""),
            phone=data.get("phone", ""),
            email=data.get("email"),
            description=data.get("description"),
            city_id=data.get("cityId"),
            neighbourhood_id=data["neighbourhoodId"]
            if "neighbourhoodId" in data
            else FIELD_UNSET,
            price_range_id=data["priceRangeId"] if "priceRangeId" in data else FIELD_UNSET,
            cuisine_type_ids=data["cuisineTypeIds"]
            if "cuisineTypeIds" in data
            else FIELD_UNSET,
        ), 200

    @namespace.response(204, "Restaurant deleted successfully.")
    @namespace.response(404, "Restaurant not found.")
    @require_restaurant_admin("restaurant_id")
    def delete(self, restaurant_id: UUID):
        """Delete a restaurant by ID."""
        RestaurantService.delete(restaurant_id)
        return "", 204


@namespace.route("/<uuid:restaurant_id>/photo")
@namespace.doc(params={"restaurant_id": "The restaurant's ID (UUID)."})
class RestaurantPhoto(Resource):
    """Endpoint for uploading a restaurant's photo to S3."""

    @namespace.expect(_photo_parser)
    @namespace.response(200, "Photo uploaded successfully.", restaurant_response_model)
    @namespace.response(400, "No file provided.")
    @namespace.response(404, "Restaurant not found.")
    @require_restaurant_admin("restaurant_id")
    def post(self, restaurant_id: UUID):
        """Upload a photo for a restaurant via multipart/form-data."""
        args = _photo_parser.parse_args()
        file = args["file"]
        return RestaurantService.upload_photo(restaurant_id, file), 200


@namespace.route("/<uuid:restaurant_id>/admins")
@namespace.doc(params={"restaurant_id": "The restaurant's ID (UUID)."})
class RestaurantAdmins(Resource):
    @namespace.response(200, "Restaurant admins retrieved successfully.", paginated_restaurant_admin_response_model)
    @namespace.response(404, "Restaurant not found.")
    @require_restaurant_admin("restaurant_id")
    def get(self, restaurant_id: UUID):
        """List all administrators assigned to a restaurant."""
        return RestaurantAdminService.list_admins(restaurant_id), 200

    @namespace.expect(restaurant_admin_add_model, validate=True)
    @namespace.response(201, "Restaurant admin added successfully.", restaurant_admin_response_model)
    @namespace.response(404, "Restaurant or user not found.")
    @namespace.response(409, "User is already an admin for this restaurant.")
    @require_restaurant_admin("restaurant_id")
    def post(self, restaurant_id: UUID):
        """Assign a user as administrator of a restaurant."""
        data = request.json
        return RestaurantAdminService.add_admin(
            restaurant_id=restaurant_id,
            user_id=data.get("userId"),
        ), 201


@namespace.route("/<uuid:restaurant_id>/admins/<uuid:user_id>")
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
    def delete(self, restaurant_id: UUID, user_id: UUID):
        """Remove a user from the administrators of a restaurant."""
        RestaurantAdminService.remove_admin(restaurant_id=restaurant_id, user_id=user_id)
        return "", 204


@namespace.route("/<uuid:restaurant_id>/analytics/orders")
@namespace.doc(params={"restaurant_id": "The restaurant's ID (UUID)."})
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
    def get(self, restaurant_id: UUID):
        """Get orders analytics report for a restaurant within a date range."""
        args = _analytics_date_range_parser.parse_args()
        return AnalyticsService.get_orders_report(
            restaurant_id=restaurant_id,
            start=args.get("start"),
            end=args.get("end"),
        ), 200

@namespace.route("/<uuid:restaurant_id>/analytics/metrics")
@namespace.doc(params={"restaurant_id": "The restaurant's ID (UUID)."})
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
    def get(self, restaurant_id: UUID):
        """Get general metrics for a restaurant (orders, reservations, revenue) within a date range."""
        args = _analytics_date_range_parser.parse_args()
        return AnalyticsService.get_general_metrics(
            restaurant_id=restaurant_id,
            start=args.get("start"),
            end=args.get("end"),
        ), 200