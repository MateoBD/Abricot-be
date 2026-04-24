import logging
from uuid import UUID

from app.exceptions.errors import ConflictError, NotFoundError, ValidationError
from app.models.enums import UserRole
from app.repositories.restaurant_admin_repository import RestaurantAdminRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.user_repository import UserRepository
from app.utils.list_envelope import list_envelope

logger = logging.getLogger(__name__)


def _parse_user_uuid(value: str | UUID | None, field: str) -> UUID:
    if value is None or value == "":
        raise ValidationError(f"{field} is required.", {field: "Required"})
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError:
        raise ValidationError("Invalid identifier format.", {field: "Invalid UUID"})


class RestaurantAdminService:
    @staticmethod
    def list_admins(restaurant_id: UUID) -> dict:
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")

        user_ids = RestaurantAdminRepository.get_admin_user_ids_for_restaurant(restaurant_id)
        admins: list[dict] = []
        for user_id in user_ids:
            user = UserRepository.get_by_id(user_id)
            if user:
                admins.append(user.to_dict())

        return list_envelope(admins)

    @staticmethod
    def add_admin(restaurant_id: UUID, user_id: str | UUID) -> dict:
        uid = _parse_user_uuid(user_id, "userId")
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")

        user = UserRepository.get_by_id(uid)
        if not user:
            raise NotFoundError(f"User with id={uid} not found.")

        if RestaurantAdminRepository.is_admin(user_id=uid, restaurant_id=restaurant_id):
            raise ConflictError(
                "User is already an admin for this restaurant.",
                {"userId": "Already admin"},
            )

        RestaurantAdminRepository.add(user_id=uid, restaurant_id=restaurant_id)

        if user.role == UserRole.CUSTOMER:
            UserRepository.update_role(user_id=uid, role=UserRole.RESTAURANT_ADMIN)

        logger.info(
            "Restaurant admin added: restaurant_id=%s user_id=%s",
            restaurant_id,
            uid,
        )
        return UserRepository.get_by_id(uid).to_dict()

    @staticmethod
    def is_admin(user_id: UUID, restaurant_id: UUID) -> bool:
        return RestaurantAdminRepository.is_admin(user_id=user_id, restaurant_id=restaurant_id)

    @staticmethod
    def get_restaurants_for_admin(user_id: UUID) -> dict:
        user = UserRepository.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with id={user_id} not found.")

        restaurant_ids = RestaurantAdminRepository.get_restaurants_for_user(user_id)
        restaurants = []
        for rid in restaurant_ids:
            restaurant = RestaurantRepository.get_by_id(rid)
            if restaurant:
                restaurants.append(restaurant.to_dict())

        return list_envelope(restaurants)

    @staticmethod
    def remove_admin(restaurant_id: UUID, user_id: UUID) -> None:
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")

        user = UserRepository.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with id={user_id} not found.")

        removed = RestaurantAdminRepository.remove(user_id=user_id, restaurant_id=restaurant_id)
        if not removed:
            raise NotFoundError(
                f"User with id={user_id} is not an admin for restaurant id={restaurant_id}."
            )

        remaining_restaurants = RestaurantAdminRepository.get_restaurants_for_user(user_id)
        if not remaining_restaurants and user.role == UserRole.RESTAURANT_ADMIN:
            UserRepository.update_role(user_id=user_id, role=UserRole.CUSTOMER)

        logger.info(
            "Restaurant admin removed: restaurant_id=%s user_id=%s",
            restaurant_id,
            user_id,
        )
