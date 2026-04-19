from flask import request
from flask_restx import Namespace, Resource, reqparse
from werkzeug.datastructures import FileStorage

from app.api.restaurants.schemas import (
    restaurant_create_model,
    restaurant_response_model,
    restaurant_update_model,
)
from app.exceptions.errors import ValidationError
from app.middleware.auth import require_authentication
from app.services.restaurant_service import RestaurantService

namespace = Namespace(
    name="Restaurants",
    path="/restaurants",
    description="ABM de restaurantes.",
    decorators=[require_authentication()],
)

for _model in (restaurant_create_model, restaurant_update_model, restaurant_response_model):
    namespace.models[_model.name] = _model

_photo_parser = reqparse.RequestParser()
_photo_parser.add_argument(
    "file",
    type=FileStorage,
    location="files",
    required=True,
    help="Image file to upload.",
)


@namespace.route("/")
class RestaurantList(Resource):
    """Endpoints for listing and creating restaurants."""

    @namespace.response(200, "Restaurants retrieved successfully.", [restaurant_response_model])
    def get(self):
        """List all restaurants ordered alphabetically by name."""
        return RestaurantService.get_all(), 200

    @namespace.expect(restaurant_create_model, validate=True)
    @namespace.response(201, "Restaurant created successfully.", restaurant_response_model)
    @namespace.response(400, "Validation error.")
    def post(self):
        """Create a new restaurant."""
        data = request.json
        return RestaurantService.create(
            name=data.get("name", ""),
            address=data.get("address", ""),
            phone=data.get("phone", ""),
            email=data.get("email"),
            description=data.get("description"),
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
    def post(self, restaurant_id: int):
        """Upload a photo for a restaurant via multipart/form-data."""
        args = _photo_parser.parse_args()
        file = args["file"]
        if not file:
            raise ValidationError("No file provided.")
        return RestaurantService.upload_photo(restaurant_id, file), 200
