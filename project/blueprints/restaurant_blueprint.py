import logging

from flask import request
from flask_restx import Namespace, Resource, reqparse
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import NotFound, UnprocessableEntity

from project.blueprints.models.restaurant_models import (
    restaurant_create_model,
    restaurant_response_model,
    restaurant_update_model,
)
from project.exceptions.restaurant_exception import RestaurantException
from project.helpers.authentication import require_authentication
from project.helpers.s3 import S3Service
from project.repositories.restaurant_repository import RestaurantRepository

logger = logging.getLogger(__name__)

namespace = Namespace(
    name="Restaurants",
    path="/restaurants",
    description="ABM de restaurantes.",
    decorators=[require_authentication()],
)

namespace.models[restaurant_create_model.name] = restaurant_create_model
namespace.models[restaurant_update_model.name] = restaurant_update_model
namespace.models[restaurant_response_model.name] = restaurant_response_model

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

    @namespace.response(
        200, "Restaurants retrieved successfully.", [restaurant_response_model]
    )
    def get(self):
        """
        List all restaurants.

        Returns a list of all restaurants ordered alphabetically by name.
        Requires a valid JWT in the Authorization header.
        """
        restaurants = RestaurantRepository.get_all()
        return [r.to_dict() for r in restaurants], 200

    @namespace.expect(restaurant_create_model, validate=True)
    @namespace.response(
        201, "Restaurant created successfully.", restaurant_response_model
    )
    @namespace.response(400, "Validation error.")
    def post(self):
        """
        Create a new restaurant.

        Requires name, address, and phone. Email and description are optional.
        Requires a valid JWT in the Authorization header.
        """
        data = request.json

        name = data.get("name", "").strip()
        address = data.get("address", "").strip()
        phone = data.get("phone", "").strip()
        email = data.get("email", "").strip() or None
        description = data.get("description", "").strip() or None

        if not name:
            raise RestaurantException("Name is required.", {"name": "Cannot be empty"})

        restaurant = RestaurantRepository.create(
            name=name,
            address=address,
            phone=phone,
            email=email,
            description=description,
        )

        logger.info(f"Restaurant created: id={restaurant.id} name={restaurant.name}")

        return restaurant.to_dict(), 201


@namespace.route("/<int:restaurant_id>")
@namespace.doc(params={"restaurant_id": "The restaurant's ID."})
class RestaurantDetail(Resource):
    """Endpoints for retrieving, updating, and deleting a single restaurant."""

    @namespace.response(
        200, "Restaurant retrieved successfully.", restaurant_response_model
    )
    @namespace.response(404, "Restaurant not found.")
    def get(self, restaurant_id: int):
        """
        Get a restaurant by ID.

        Requires a valid JWT in the Authorization header.
        """
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFound(f"Restaurant with id={restaurant_id} not found.")
        return restaurant.to_dict(), 200

    @namespace.expect(restaurant_update_model, validate=True)
    @namespace.response(
        200, "Restaurant updated successfully.", restaurant_response_model
    )
    @namespace.response(404, "Restaurant not found.")
    def put(self, restaurant_id: int):
        """
        Update a restaurant by ID.

        Replaces all editable fields. Omitting email or description will clear them.
        Requires a valid JWT in the Authorization header.
        """
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFound(f"Restaurant with id={restaurant_id} not found.")

        data = request.json

        name = data.get("name", "").strip()
        address = data.get("address", "").strip()
        phone = data.get("phone", "").strip()
        email = data.get("email", "").strip() or None
        description = data.get("description", "").strip() or None

        if not name:
            raise RestaurantException("Name is required.", {"name": "Cannot be empty"})

        restaurant = RestaurantRepository.update(
            restaurant=restaurant,
            name=name,
            address=address,
            phone=phone,
            email=email,
            description=description,
        )

        logger.info(f"Restaurant updated: id={restaurant.id} name={restaurant.name}")

        return restaurant.to_dict(), 200

    @namespace.response(204, "Restaurant deleted successfully.")
    @namespace.response(404, "Restaurant not found.")
    def delete(self, restaurant_id: int):
        """
        Delete a restaurant by ID.

        Requires a valid JWT in the Authorization header.
        """
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFound(f"Restaurant with id={restaurant_id} not found.")

        RestaurantRepository.delete(restaurant)

        logger.info(f"Restaurant deleted: id={restaurant_id}")

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
        """
        Upload a photo for a restaurant.

        Accepts multipart/form-data with a 'file' field.
        The image is stored in S3 and the URL is saved on the restaurant.
        Requires a valid JWT in the Authorization header.
        """
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFound(f"Restaurant with id={restaurant_id} not found.")

        args = _photo_parser.parse_args()
        file = args["file"]

        if not file:
            raise UnprocessableEntity("No file provided.")

        photo_url = S3Service.upload_restaurant_photo(file, restaurant_id)

        restaurant = RestaurantRepository.update_photo(restaurant, photo_url)

        logger.info(f"Restaurant photo uploaded: id={restaurant_id} url={photo_url}")

        return restaurant.to_dict(), 200
