import logging
from uuid import UUID

from app.exceptions.errors import NotFoundError, ValidationError
from app.repositories.menu_category_repository import MenuCategoryRepository
from app.repositories.menu_item_repository import MenuItemRepository
from app.repositories.menu_repository import MenuRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.utils.list_envelope import list_envelope

logger = logging.getLogger(__name__)


def _category_detail(category) -> dict:
    items = MenuItemRepository.get_all(category.id)
    return {**category.to_dict(), "items": [i.to_dict() for i in items]}


class MenuService:
    @staticmethod
    def get_all(restaurant_id: UUID) -> dict:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        menus = MenuRepository.get_all(restaurant_id)
        return list_envelope([m.to_dict() for m in menus])

    @staticmethod
    def get_by_id(restaurant_id: UUID, menu_id: UUID) -> dict:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        menu = MenuRepository.get_by_id(restaurant_id, menu_id)
        if not menu:
            raise NotFoundError(f"Menu with id={menu_id} not found.")
        return menu.to_dict()

    @staticmethod
    def get_detail(restaurant_id: UUID, menu_id: UUID) -> dict:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        menu = MenuRepository.get_by_id(restaurant_id, menu_id)
        if not menu:
            raise NotFoundError(f"Menu with id={menu_id} not found.")
        categories = MenuCategoryRepository.get_all(menu.id)
        return {**menu.to_dict(), "categories": [_category_detail(c) for c in categories]}

    @staticmethod
    def create(restaurant_id: UUID, name: str) -> dict:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        name = (name or "").strip()
        if not name:
            raise ValidationError("Name is required.", {"name": "Cannot be empty"})
        menu = MenuRepository.create(restaurant_id, name)
        logger.info("Menu created: restaurant_id=%s menu_id=%s", restaurant_id, menu.id)
        return menu.to_dict()

    @staticmethod
    def update(restaurant_id: UUID, menu_id: UUID, name: str) -> dict:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        menu = MenuRepository.get_by_id(restaurant_id, menu_id)
        if not menu:
            raise NotFoundError(f"Menu with id={menu_id} not found.")
        name = (name or "").strip()
        if not name:
            raise ValidationError("Name is required.", {"name": "Cannot be empty"})
        menu.name = name
        MenuRepository.save(menu)
        logger.info("Menu updated: menu_id=%s", menu_id)
        return menu.to_dict()

    @staticmethod
    def delete(restaurant_id: UUID, menu_id: UUID) -> None:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        menu = MenuRepository.get_by_id(restaurant_id, menu_id)
        if not menu:
            raise NotFoundError(f"Menu with id={menu_id} not found.")
        MenuRepository.delete(menu)
        logger.info("Menu deleted: menu_id=%s", menu_id)

    @staticmethod
    def activate(restaurant_id: UUID, menu_id: UUID) -> dict:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        menu = MenuRepository.get_by_id(restaurant_id, menu_id)
        if not menu:
            raise NotFoundError(f"Menu with id={menu_id} not found.")
        menu = MenuRepository.activate(restaurant_id, menu_id)
        logger.info("Menu activated: menu_id=%s", menu_id)
        return menu.to_dict()

    @staticmethod
    def deactivate(restaurant_id: UUID, menu_id: UUID) -> dict:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        menu = MenuRepository.get_by_id(restaurant_id, menu_id)
        if not menu:
            raise NotFoundError(f"Menu with id={menu_id} not found.")
        menu = MenuRepository.deactivate(restaurant_id, menu_id)
        logger.info("Menu deactivated: menu_id=%s", menu_id)
        return menu.to_dict()

    @staticmethod
    def get_active_menu(restaurant_id: UUID) -> dict | None:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        menu = MenuRepository.get_active(restaurant_id)
        if not menu:
            return None
        categories = MenuCategoryRepository.get_all(menu.id)
        return {**menu.to_dict(), "categories": [_category_detail(c) for c in categories]}
