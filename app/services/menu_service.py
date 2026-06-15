import logging
from uuid import UUID

from app.exceptions.errors import NotFoundError, ValidationError
from app.repositories.menu_category_repository import MenuCategoryRepository
from app.repositories.menu_item_repository import MenuItemRepository
from app.repositories.menu_repository import MenuRepository
from app.repositories.promotion_repository import PromotionRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.menu_item_service import menu_item_payload
from app.services.promotion_pricing import best_promo
from app.utils.list_envelope import list_envelope

logger = logging.getLogger(__name__)


def _item_with_promo(item, promo_map: dict) -> dict:
    """Item payload enriched with the best active promo (if any).

    Always adds `discountedPrice` and `discount`: null when no active promo
    targets the item, so the base `price` stands.
    """
    payload = menu_item_payload(item)
    chosen = best_promo(item.price, promo_map.get(item.id, []))
    if chosen is None:
        payload["discountedPrice"] = None
        payload["discount"] = None
        return payload
    effective, promo = chosen
    payload["discountedPrice"] = f"{effective:.2f}"
    payload["discount"] = {
        "promotionId": str(promo.id),
        "title": promo.title,
        "discountType": promo.discount_type.value,
        "discountValue": f"{promo.discount_value:.2f}",
    }
    return payload


def _category_detail(category, promo_map: dict | None = None) -> dict:
    promo_map = promo_map or {}
    items = MenuItemRepository.get_all(category.id)
    return {
        **category.to_dict(),
        "items": [_item_with_promo(i, promo_map) for i in items],
    }


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
        promo_map = PromotionRepository.get_active_promos_by_item(restaurant_id)
        return {
            **menu.to_dict(),
            "categories": [_category_detail(c, promo_map) for c in categories],
        }

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
        promo_map = PromotionRepository.get_active_promos_by_item(restaurant_id)
        return {
            **menu.to_dict(),
            "categories": [_category_detail(c, promo_map) for c in categories],
        }
