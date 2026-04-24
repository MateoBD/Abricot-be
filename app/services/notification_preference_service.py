import logging
from uuid import UUID

from app.exceptions.errors import NotFoundError
from app.repositories.notification_preference_repository import NotificationPreferenceRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.user_repository import UserRepository
from app.utils.list_envelope import list_envelope

logger = logging.getLogger(__name__)


class NotificationPreferenceService:
    @staticmethod
    def get_all_for_user(user_id: UUID) -> dict:
        if not UserRepository.get_by_id(user_id):
            raise NotFoundError(f"User with id={user_id} not found.")
        prefs = NotificationPreferenceRepository.get_by_user(user_id)
        return list_envelope([p.to_dict() for p in prefs])

    @staticmethod
    def get_or_create(user_id: UUID, restaurant_id: UUID) -> dict:
        if not UserRepository.get_by_id(user_id):
            raise NotFoundError(f"User with id={user_id} not found.")
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        pref = NotificationPreferenceRepository.get_or_create(user_id, restaurant_id)
        return pref.to_dict()

    @staticmethod
    def update(
        user_id: UUID,
        restaurant_id: UUID,
        receive_promotions: bool,
        receive_order_updates: bool,
        receive_reservation_reminders: bool,
    ) -> dict:
        if not UserRepository.get_by_id(user_id):
            raise NotFoundError(f"User with id={user_id} not found.")
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        pref = NotificationPreferenceRepository.update(
            user_id=user_id,
            restaurant_id=restaurant_id,
            receive_promotions=receive_promotions,
            receive_order_updates=receive_order_updates,
            receive_reservation_reminders=receive_reservation_reminders,
        )
        logger.info(
            "NotificationPreference updated: user_id=%s restaurant_id=%s", user_id, restaurant_id
        )
        return pref.to_dict()
