import logging

from app.exceptions.errors import NotFoundError, ValidationError
from app.integrations.s3 import S3Client
from app.repositories.restaurant_admin_repository import RestaurantAdminRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.utils.list_envelope import list_envelope

logger = logging.getLogger(__name__)


class RestaurantService:
    _ALLOWED_PHOTO_MIME_TYPES = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    @staticmethod
    def get_all() -> dict:
        rows = [r.to_dict() for r in RestaurantRepository.get_all()]
        return list_envelope(rows)

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
        creator_user_id: int | None = None,
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

        if creator_user_id is not None:
            RestaurantAdminRepository.add_if_missing(
                user_id=creator_user_id,
                restaurant_id=restaurant.id,
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
        if not file_storage:
            raise ValidationError("No file provided.", {"file": "Missing file"})

        mime_type = (getattr(file_storage, "mimetype", None) or "").lower()
        if mime_type not in RestaurantService._ALLOWED_PHOTO_MIME_TYPES:
            raise ValidationError(
                "Invalid file format.",
                {
                    "file": (
                        "Allowed MIME types are image/jpeg, image/png, image/webp."
                    )
                },
            )

        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        photo_url = S3Client.get().upload_restaurant_photo(file_storage, restaurant_id)
        restaurant = RestaurantRepository.update_photo(restaurant, photo_url)
        logger.info(f"Restaurant photo uploaded: id={restaurant_id}")
        return restaurant.to_dict()
