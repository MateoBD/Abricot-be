import logging

from app.exceptions.errors import NotFoundError, ValidationError
from app.integrations.s3 import S3Client
from app.repositories.restaurant_repository import RestaurantRepository

logger = logging.getLogger(__name__)


class RestaurantService:
    @staticmethod
    def get_all() -> list[dict]:
        return [r.to_dict() for r in RestaurantRepository.get_all()]

    @staticmethod
    def get_by_id(restaurant_id: int) -> dict:
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        return restaurant.to_dict()

    @staticmethod
    def create(
        name: str,
        address: str,
        phone: str,
        email: str | None = None,
        description: str | None = None,
    ) -> dict:
        name = name.strip()
        address = address.strip()
        phone = phone.strip()
        email = (email or "").strip() or None
        description = (description or "").strip() or None

        if not name:
            raise ValidationError("Name is required.", {"name": "Cannot be empty"})

        restaurant = RestaurantRepository.create(
            name=name, address=address, phone=phone, email=email, description=description
        )
        logger.info(f"Restaurant created: id={restaurant.id} name={restaurant.name}")
        return restaurant.to_dict()

    @staticmethod
    def update(
        restaurant_id: int,
        name: str,
        address: str,
        phone: str,
        email: str | None = None,
        description: str | None = None,
    ) -> dict:
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")

        name = name.strip()
        address = address.strip()
        phone = phone.strip()
        email = (email or "").strip() or None
        description = (description or "").strip() or None

        if not name:
            raise ValidationError("Name is required.", {"name": "Cannot be empty"})

        restaurant = RestaurantRepository.update(
            restaurant=restaurant,
            name=name,
            address=address,
            phone=phone,
            email=email,
            description=description,
        )
        logger.info(f"Restaurant updated: id={restaurant.id}")
        return restaurant.to_dict()

    @staticmethod
    def delete(restaurant_id: int) -> None:
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        RestaurantRepository.delete(restaurant)
        logger.info(f"Restaurant deleted: id={restaurant_id}")

    @staticmethod
    def upload_photo(restaurant_id: int, file_storage) -> dict:
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        photo_url = S3Client.get().upload_restaurant_photo(file_storage, restaurant_id)
        restaurant = RestaurantRepository.update_photo(restaurant, photo_url)
        logger.info(f"Restaurant photo uploaded: id={restaurant_id}")
        return restaurant.to_dict()
