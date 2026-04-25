from uuid import UUID

from flask import request
from flask_restx import Namespace, Resource, reqparse
from werkzeug.datastructures import FileStorage

from app.exceptions.errors import ValidationError
from app.api.restaurants.schemas import (
    analytics_period_model,
    availability_response_model,
    availability_slot_model,
    business_hours_bulk_update_model,
    business_hours_item_model,
    business_hours_response_model,
    orders_by_status_item_model,
    orders_metrics_model,
    paginated_business_hours_response_model,
    paginated_restaurant_admin_response_model,
    paginated_reservation_response_model,
    paginated_restaurant_response_model,
    paginated_table_response_model,
    general_metrics_response_model,
    orders_report_response_model,
    reservation_admin_create_model,
    reservation_cancel_model,
    reservation_create_model,
    reservation_response_model,
    reservation_table_assignment_item_model,
    restaurant_admin_add_model,
    restaurant_admin_response_model,
    restaurant_create_model,
    restaurant_response_model,
    restaurant_update_model,
    table_assignment_item_model,
    table_bulk_create_model,
    table_create_model,
    table_group_model,
    table_response_model,
    table_update_model,
    my_restaurant_review_request_model,
    my_restaurant_review_response_model,
    restaurant_order_item_admin_model,
    restaurant_order_create_item_model,
    restaurant_order_create_model,
    restaurant_order_list_admin_model,
    restaurant_order_detail_admin_model,
    restaurant_order_create_response_model,
    paginated_restaurant_orders_admin_model,
    restaurant_order_status_patch_model,
    promotion_create_model,
    promotion_response_model,
    promotions_admin_list_envelope_model,
    reservations_by_status_item_model,
    reservations_metrics_model,
    revenue_by_day_item_model,
)
from app.middleware.auth import (
    get_current_user_id,
    require_authentication,
    require_restaurant_admin,
    require_roles,
)
from app.models.enums import UserRole
from app.services.analytics_service import AnalyticsService
from app.services.availability_service import AvailabilityService
from app.services.business_hours_service import BusinessHoursService
from app.services.order_service import OrderService
from app.services.promotion_service import PromotionService
from app.services.reservation_service import ReservationService
from app.services.restaurant_admin_service import RestaurantAdminService
from app.services.restaurant_review_service import RestaurantReviewService
from app.services.restaurant_service import FIELD_UNSET, RestaurantService
from app.services.table_service import TableService


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
)

for _model in (
    restaurant_create_model,
    restaurant_update_model,
    paginated_restaurant_response_model,
    paginated_restaurant_admin_response_model,
    restaurant_response_model,
    restaurant_admin_add_model,
    restaurant_admin_response_model,
    analytics_period_model,
    orders_by_status_item_model,
    revenue_by_day_item_model,
    reservations_by_status_item_model,
    orders_metrics_model,
    reservations_metrics_model,
    orders_report_response_model,
    general_metrics_response_model,
    availability_response_model,
    reservation_create_model,
    reservation_admin_create_model,
    reservation_cancel_model,
    reservation_table_assignment_item_model,
    reservation_response_model,
    paginated_reservation_response_model,
    table_create_model,
    table_update_model,
    table_bulk_create_model,
    table_group_model,
    table_response_model,
    paginated_table_response_model,
    business_hours_item_model,
    business_hours_bulk_update_model,
    business_hours_response_model,
    paginated_business_hours_response_model,
    table_assignment_item_model,
    availability_slot_model,
    my_restaurant_review_request_model,
    my_restaurant_review_response_model,
    restaurant_order_item_admin_model,
    restaurant_order_create_item_model,
    restaurant_order_create_model,
    restaurant_order_list_admin_model,
    restaurant_order_detail_admin_model,
    restaurant_order_create_response_model,
    paginated_restaurant_orders_admin_model,
    restaurant_order_status_patch_model,
    promotion_create_model,
    promotion_response_model,
    promotions_admin_list_envelope_model,
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

_reservations_list_parser = reqparse.RequestParser()
_reservations_list_parser.add_argument(
    "date",
    type=str,
    location="args",
    required=False,
    help="Reservation date in YYYY-MM-DD format.",
)
_reservations_list_parser.add_argument(
    "status",
    type=str,
    location="args",
    required=False,
    help="Reservation status: CONFIRMED, CANCELLED, COMPLETED, NO_SHOW.",
)
_reservations_list_parser.add_argument(
    "source",
    type=str,
    location="args",
    required=False,
    help="Reservation source: ONLINE, PHONE, EVENT.",
)
_reservations_list_parser.add_argument(
    "page",
    type=int,
    location="args",
    required=False,
    default=1,
    help="Page number (1-based).",
)
_reservations_list_parser.add_argument(
    "perPage",
    type=int,
    location="args",
    required=False,
    default=20,
    help="Items per page (max 100).",
)

_availability_parser = reqparse.RequestParser()
_availability_parser.add_argument(
    "date",
    type=str,
    location="args",
    required=True,
    help="Availability date in YYYY-MM-DD format.",
)
_availability_parser.add_argument(
    "partySize",
    type=int,
    location="args",
    required=True,
    help="Party size (must be >= 1).",
)

_restaurant_orders_list_parser = reqparse.RequestParser()
_restaurant_orders_list_parser.add_argument(
    "page",
    type=int,
    location="args",
    default=1,
    help="Page number (1-based).",
)
_restaurant_orders_list_parser.add_argument(
    "perPage",
    type=int,
    location="args",
    default=20,
    help="Items per page (max 100).",
)
_restaurant_orders_list_parser.add_argument(
    "status",
    type=str,
    location="args",
    required=False,
    help="Filter by order status (PENDING, CONFIRMED, IN_PREPARATION, READY, COMPLETED, CANCELLED).",
)


@namespace.route("/")
class RestaurantList(Resource):
    """Endpoints for listing and creating restaurants."""

    @namespace.response(
        200, "Restaurants retrieved successfully.", paginated_restaurant_response_model
    )
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
    @namespace.response(
        201, "Restaurant created successfully.", restaurant_response_model
    )
    @namespace.response(400, "Validation error.")
    @require_authentication()
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

    @namespace.response(
        200, "Restaurant retrieved successfully.", restaurant_response_model
    )
    @namespace.response(404, "Restaurant not found.")
    def get(self, restaurant_id: UUID):
        """Get a restaurant by ID."""
        return RestaurantService.get_by_id(restaurant_id), 200

    @namespace.expect(restaurant_update_model, validate=True)
    @namespace.response(
        200, "Restaurant updated successfully.", restaurant_response_model
    )
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
            price_range_id=data["priceRangeId"]
            if "priceRangeId" in data
            else FIELD_UNSET,
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


@namespace.route("/<uuid:restaurant_id>/my-review")
@namespace.doc(
    params={"restaurant_id": "The restaurant's ID (UUID)."},
    description=(
        "Un usuario autenticado solo puede tener una puntuación por restaurante: "
        "el mismo PUT actualiza su nota. El promedio del restaurante sale en "
        "GET de restaurante / listado."
    ),
)
class MyRestaurantReview(Resource):
    @namespace.expect(my_restaurant_review_request_model, validate=True)
    @namespace.response(200, "Reseña guardada o actualizada.", my_restaurant_review_response_model)
    @namespace.response(400, "Validation error.")
    @namespace.response(404, "Restaurant not found.")
    @require_authentication()
    def put(self, restaurant_id: UUID):
        """Crear o reemplazar la puntuación (1–5) del usuario para este restaurante."""
        data = request.json or {}
        return (
            RestaurantReviewService.set_my_review(
                get_current_user_id(),
                restaurant_id,
                data.get("score"),
            ),
            200,
        )


# ── Takeout orders ─────────────────────────────────────────────────────────────


@namespace.route("/<uuid:restaurant_id>/orders")
@namespace.doc(
    params={"restaurant_id": "The restaurant's ID (UUID)."},
    description="Takeout orders for this restaurant (authenticated users can create; admins can list).",
)
class RestaurantOrdersForAdmin(Resource):
    @namespace.expect(restaurant_order_create_model, validate=True)
    @namespace.response(201, "Order created successfully.", restaurant_order_create_response_model)
    @namespace.response(400, "Validation error.")
    @namespace.response(401, "Unauthorized.")
    @namespace.response(404, "Restaurant not found or has no active menu.")
    @require_authentication()
    def post(self, restaurant_id: UUID):
        """Create a takeout order for this restaurant using the active menu."""
        data = request.json or {}
        return (
            OrderService.create(
                restaurant_id=restaurant_id,
                user_id=get_current_user_id(),
                items=data.get("items") or [],
                notes=data.get("notes"),
            ),
            201,
        )

    @namespace.expect(_restaurant_orders_list_parser)
    @namespace.response(
        200,
        "Orders retrieved successfully.",
        paginated_restaurant_orders_admin_model,
    )
    @namespace.response(400, "Validation error.")
    @namespace.response(404, "Restaurant not found.")
    @require_restaurant_admin("restaurant_id")
    def get(self, restaurant_id: UUID):
        """List takeout orders, optional `status` filter, paginated (`page`, `perPage`)."""
        args = _restaurant_orders_list_parser.parse_args()
        return (
            OrderService.list_for_restaurant(
                restaurant_id=restaurant_id,
                status_filter=args.get("status"),
                page=args.get("page") or 1,
                per_page=args.get("perPage") or 20,
            ),
            200,
        )


@namespace.route("/<uuid:restaurant_id>/orders/<uuid:order_id>")
@namespace.doc(
    params={
        "restaurant_id": "The restaurant's ID (UUID).",
        "order_id": "The takeout order's ID (UUID).",
    }
)
class RestaurantOrderAdminDetail(Resource):
    @namespace.response(
        200,
        "Order with line items.",
        restaurant_order_detail_admin_model,
    )
    @namespace.response(404, "Restaurant or order not found.")
    @require_restaurant_admin("restaurant_id")
    def get(self, restaurant_id: UUID, order_id: UUID):
        """Get one takeout order with `items` for the kitchen or admin view."""
        return (
            OrderService.get_by_id_for_restaurant_admin(order_id, restaurant_id),
            200,
        )

    @namespace.expect(restaurant_order_status_patch_model, validate=True)
    @namespace.response(
        200,
        "Status updated. Response includes `items`.",
        restaurant_order_detail_admin_model,
    )
    @namespace.response(400, "Validation error.")
    @namespace.response(404, "Restaurant or order not found.")
    @namespace.response(409, "Invalid status transition for current state.")
    @require_restaurant_admin("restaurant_id")
    def patch(self, restaurant_id: UUID, order_id: UUID):
        """Change order state along allowed transitions (see OrderService)."""
        data = request.json or {}
        return (
            OrderService.update_status(
                order_id=order_id,
                new_status_str=str(data.get("status", "")),
                estimated_ready_at=data.get("estimatedReadyAt"),
                restaurant_id=restaurant_id,
            ),
            200,
        )


# ── Promotions (restaurant admin) ─────────────────────────────────────────────


@namespace.route("/<uuid:restaurant_id>/promotions")
@namespace.doc(
    params={"restaurant_id": "The restaurant's ID (UUID)."},
    description="Promociones: listado y alta (admin del restaurante o SUPER_ADMIN).",
)
class RestaurantPromotionsForAdmin(Resource):
    @namespace.response(200, "List of promotions (includes menuItemIds).", promotions_admin_list_envelope_model)
    @namespace.response(404, "Restaurant not found.")
    @require_restaurant_admin("restaurant_id")
    def get(self, restaurant_id: UUID):
        """List all promotions for this restaurant (including inactive / outside date range)."""
        return PromotionService.get_all_for_admin(restaurant_id), 200

    @namespace.expect(promotion_create_model, validate=True)
    @namespace.response(201, "Promotion created.", promotion_response_model)
    @namespace.response(400, "Validation error.")
    @namespace.response(404, "Restaurant not found.")
    @require_restaurant_admin("restaurant_id")
    def post(self, restaurant_id: UUID):
        """Create a promotion; optional `notifyUsers` may trigger email to opted-in customers."""
        data = request.json or {}
        return (
            PromotionService.create(
                restaurant_id=restaurant_id,
                title=data.get("title", ""),
                description=data.get("description"),
                discount_type=str(data.get("discountType", "")),
                discount_value=data.get("discountValue"),
                start_date=str(data.get("startDate", "")),
                end_date=str(data.get("endDate", "")),
                notify_users=bool(data.get("notifyUsers", False)),
                menu_item_ids=data.get("menuItemIds"),
            ),
            201,
        )


@namespace.route("/<uuid:restaurant_id>/promotions/<uuid:promotion_id>")
@namespace.doc(
    params={
        "restaurant_id": "The restaurant's ID (UUID).",
        "promotion_id": "The promotion's ID (UUID).",
    }
)
class RestaurantPromotionAdminDetail(Resource):
    @namespace.response(200, "Promotion with menuItemIds.", promotion_response_model)
    @namespace.response(404, "Restaurant or promotion not found.")
    @require_restaurant_admin("restaurant_id")
    def get(self, restaurant_id: UUID, promotion_id: UUID):
        """Get one promotion by id."""
        return PromotionService.get_by_id(restaurant_id, promotion_id), 200

    @namespace.response(204, "Deleted.")
    @namespace.response(404, "Restaurant or promotion not found.")
    @require_restaurant_admin("restaurant_id")
    def delete(self, restaurant_id: UUID, promotion_id: UUID):
        """Delete a promotion and its menu-item links."""
        PromotionService.delete(restaurant_id, promotion_id)
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
    @namespace.response(
        200,
        "Restaurant admins retrieved successfully.",
        paginated_restaurant_admin_response_model,
    )
    @namespace.response(404, "Restaurant not found.")
    @require_restaurant_admin("restaurant_id")
    def get(self, restaurant_id: UUID):
        """List all administrators assigned to a restaurant."""
        return RestaurantAdminService.list_admins(restaurant_id), 200

    @namespace.expect(restaurant_admin_add_model, validate=True)
    @namespace.response(
        201, "Restaurant admin added successfully.", restaurant_admin_response_model
    )
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
        RestaurantAdminService.remove_admin(
            restaurant_id=restaurant_id, user_id=user_id
        )
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


@namespace.route("/<uuid:restaurant_id>/reservations")
@namespace.doc(params={"restaurant_id": "The restaurant's ID (UUID)."})
class RestaurantReservationList(Resource):
    @namespace.response(
        200,
        "Reservations retrieved successfully.",
        paginated_reservation_response_model,
    )
    @namespace.response(400, "Validation error.")
    @namespace.response(404, "Restaurant not found.")
    @namespace.expect(_reservations_list_parser)
    @require_restaurant_admin("restaurant_id")
    def get(self, restaurant_id: UUID):
        """List restaurant reservations with optional filters and pagination."""
        args = _reservations_list_parser.parse_args()
        return ReservationService.list_for_restaurant(
            restaurant_id=restaurant_id,
            on_date=args.get("date"),
            status=args.get("status"),
            source=args.get("source"),
            page=args.get("page") or 1,
            per_page=args.get("perPage") or 20,
        ), 200

    @namespace.expect(reservation_create_model, validate=True)
    @namespace.response(201, "Reservation created successfully.", reservation_response_model)
    @namespace.response(400, "Validation error.")
    @namespace.response(404, "Restaurant not found.")
    @namespace.response(409, "No table availability for requested slot.")
    @require_authentication()
    def post(self, restaurant_id: UUID):
        """Create a reservation as a logged-in customer (source=ONLINE)."""
        data = request.json or {}
        return ReservationService.create(
            restaurant_id=restaurant_id,
            user_id=get_current_user_id(),
            party_size=data.get("partySize"),
            on_date=ReservationService.parse_required_date(data.get("date")),
            time_slot=ReservationService.parse_required_time(data.get("timeSlot")),
            notes=data.get("notes"),
        ), 201

@namespace.route("/<uuid:restaurant_id>/reservations/admin")
@namespace.doc(params={"restaurant_id": "The restaurant's ID (UUID)."})
class RestaurantReservationAdminCreate(Resource):
    @namespace.expect(reservation_admin_create_model, validate=True)
    @namespace.response(201, "Reservation created successfully.", reservation_response_model)
    @namespace.response(400, "Validation error.")
    @namespace.response(403, "Forbidden.")
    @namespace.response(404, "Restaurant or user not found.")
    @namespace.response(409, "No table availability for requested slot.")
    @require_restaurant_admin("restaurant_id")
    def post(self, restaurant_id: UUID):
        """Create a reservation as restaurant admin for PHONE/EVENT source."""
        data = request.json or {}

        user_id_raw = data.get("userId")
        user_id = None
        if user_id_raw is not None:
            try:
                user_id = UUID(str(user_id_raw))
            except (TypeError, ValueError) as error:
                raise ValidationError(
                    "Invalid userId.",
                    {"userId": "Must be a valid UUID"},
                ) from error

        return ReservationService.create_for_admin(
            restaurant_id=restaurant_id,
            admin_user_id=get_current_user_id(),
            party_size=data.get("partySize"),
            on_date=ReservationService.parse_required_date(data.get("date")),
            time_slot=ReservationService.parse_required_time(data.get("timeSlot")),
            source=ReservationService.parse_required_admin_source(data.get("source")),
            guest_name=data.get("guestName"),
            guest_phone=data.get("guestPhone"),
            guest_email=data.get("guestEmail"),
            user_id=user_id,
            notes=data.get("notes"),
        ), 201


@namespace.route("/<uuid:restaurant_id>/reservations/<uuid:reservation_id>")
@namespace.doc(
    params={
        "restaurant_id": "The restaurant's ID (UUID).",
        "reservation_id": "The reservation's ID (UUID).",
    }
)
class RestaurantReservationDetail(Resource):
    @namespace.response(200, "Reservation retrieved successfully.", reservation_response_model)
    @namespace.response(403, "Forbidden.")
    @namespace.response(404, "Reservation not found.")
    @require_restaurant_admin("restaurant_id")
    def get(self, restaurant_id: UUID, reservation_id: UUID):
        """Get a single reservation for the given restaurant."""
        return ReservationService.get_by_id(
            reservation_id=reservation_id,
            requesting_user_id=get_current_user_id(),
            restaurant_id=restaurant_id,
        ), 200


@namespace.route("/<uuid:restaurant_id>/reservations/<uuid:reservation_id>/cancel")
@namespace.doc(
    params={
        "restaurant_id": "The restaurant's ID (UUID).",
        "reservation_id": "The reservation's ID (UUID).",
    }
)
class RestaurantReservationCancel(Resource):
    @namespace.expect(reservation_cancel_model, validate=True)
    @namespace.response(200, "Reservation cancelled successfully.", reservation_response_model)
    @namespace.response(403, "Forbidden.")
    @namespace.response(404, "Reservation not found.")
    @namespace.response(409, "Reservation cannot be cancelled in current status.")
    @require_authentication()
    def post(self, restaurant_id: UUID, reservation_id: UUID):
        """Cancel a reservation and release assigned tables."""
        data = request.json or {}
        return ReservationService.cancel(
            reservation_id=reservation_id,
            requesting_user_id=get_current_user_id(),
            reason=data.get("reason"),
            restaurant_id=restaurant_id,
        ), 200


# ── Tables ───────────────────────────────────────────────────────────────────


@namespace.route("/<uuid:restaurant_id>/tables")
@namespace.doc(params={"restaurant_id": "The restaurant's ID (UUID)."})
class RestaurantTableList(Resource):
    @namespace.response(200, "Tables retrieved successfully.", paginated_table_response_model)
    @namespace.response(404, "Restaurant not found.")
    @require_restaurant_admin("restaurant_id")
    def get(self, restaurant_id: UUID):
        """List all tables for a restaurant."""
        return TableService.get_all(restaurant_id), 200

    @namespace.expect(table_create_model, validate=True)
    @namespace.response(201, "Table created successfully.", table_response_model)
    @namespace.response(400, "Validation error.")
    @namespace.response(404, "Restaurant not found.")
    @namespace.response(409, "Table number already exists for this restaurant.")
    @require_restaurant_admin("restaurant_id")
    def post(self, restaurant_id: UUID):
        """Create a single table for a restaurant."""
        data = request.json or {}
        return TableService.create(
            restaurant_id=restaurant_id,
            number=data.get("number"),
            capacity=data.get("capacity"),
            name=data.get("name"),
            is_joinable=data.get("isJoinable", True),
        ), 201


@namespace.route("/<uuid:restaurant_id>/tables/bulk")
@namespace.doc(params={"restaurant_id": "The restaurant's ID (UUID)."})
class RestaurantTableBulk(Resource):
    @namespace.expect(table_bulk_create_model, validate=True)
    @namespace.response(201, "Tables created successfully.", paginated_table_response_model)
    @namespace.response(400, "Validation error.")
    @namespace.response(404, "Restaurant not found.")
    @require_restaurant_admin("restaurant_id")
    def post(self, restaurant_id: UUID):
        """Bulk-create tables from groups of {quantity, capacity, isJoinable}."""
        data = request.json or {}
        return TableService.create_bulk(
            restaurant_id=restaurant_id,
            groups=data.get("groups", []),
        ), 201


@namespace.route("/<uuid:restaurant_id>/tables/<uuid:table_id>")
@namespace.doc(
    params={
        "restaurant_id": "The restaurant's ID (UUID).",
        "table_id": "The table's ID (UUID).",
    }
)
class RestaurantTableDetail(Resource):
    @namespace.response(200, "Table retrieved successfully.", table_response_model)
    @namespace.response(404, "Restaurant or table not found.")
    @require_restaurant_admin("restaurant_id")
    def get(self, restaurant_id: UUID, table_id: UUID):
        """Get a single table by ID."""
        return TableService.get_by_id(restaurant_id, table_id), 200

    @namespace.expect(table_update_model, validate=True)
    @namespace.response(200, "Table updated successfully.", table_response_model)
    @namespace.response(400, "Validation error.")
    @namespace.response(404, "Restaurant or table not found.")
    @namespace.response(409, "Table number already exists for this restaurant.")
    @require_restaurant_admin("restaurant_id")
    def put(self, restaurant_id: UUID, table_id: UUID):
        """Replace all fields of a table."""
        data = request.json or {}
        return TableService.update(
            restaurant_id=restaurant_id,
            table_id=table_id,
            number=data.get("number"),
            capacity=data.get("capacity"),
            name=data.get("name"),
            is_joinable=data.get("isJoinable", True),
            is_active=data.get("isActive", True),
        ), 200

    @namespace.response(204, "Table deleted successfully.")
    @namespace.response(404, "Restaurant or table not found.")
    @namespace.response(409, "Table has future confirmed reservations.")
    @require_restaurant_admin("restaurant_id")
    def delete(self, restaurant_id: UUID, table_id: UUID):
        """Delete a table. Fails if it has future confirmed reservations."""
        TableService.delete(restaurant_id, table_id)
        return "", 204


# ── Business Hours ────────────────────────────────────────────────────────────


@namespace.route("/<uuid:restaurant_id>/business-hours")
@namespace.doc(params={"restaurant_id": "The restaurant's ID (UUID)."})
class RestaurantBusinessHours(Resource):
    @namespace.response(
        200, "Business hours retrieved successfully.", paginated_business_hours_response_model
    )
    @namespace.response(404, "Restaurant not found.")
    @require_authentication()
    def get(self, restaurant_id: UUID):
        """Get all business hours for a restaurant."""
        return BusinessHoursService.get_all(restaurant_id), 200

    @namespace.expect(business_hours_bulk_update_model, validate=True)
    @namespace.response(
        200, "Business hours updated successfully.", paginated_business_hours_response_model
    )
    @namespace.response(400, "Validation error.")
    @namespace.response(404, "Restaurant not found.")
    @require_restaurant_admin("restaurant_id")
    def put(self, restaurant_id: UUID):
        """Upsert business hours for a restaurant (partial or full week)."""
        data = request.json or {}
        return BusinessHoursService.bulk_update(
            restaurant_id=restaurant_id,
            hours_data=data.get("hours", []),
        ), 200


# ── Availability ──────────────────────────────────────────────────────────────


@namespace.route("/<uuid:restaurant_id>/availability")
@namespace.doc(params={"restaurant_id": "The restaurant's ID (UUID)."})
class RestaurantAvailability(Resource):
    @namespace.expect(_availability_parser)
    @namespace.response(200, "Availability retrieved successfully.", availability_response_model)
    @namespace.response(400, "Validation error.")
    @namespace.response(404, "Restaurant not found.")
    @require_authentication()
    def get(self, restaurant_id: UUID):
        """Get available time slots for a given date and party size."""
        args = _availability_parser.parse_args()
        raw_date = args.get("date")
        party_size = args.get("partySize")
        on_date = ReservationService.parse_required_date(raw_date)
        slots = AvailabilityService.get_available_slots(restaurant_id, on_date, party_size)
        return {
            "date": on_date.isoformat(),
            "partySize": party_size,
            "slots": slots,
        }, 200
