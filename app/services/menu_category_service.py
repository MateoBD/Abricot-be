import logging
from uuid import UUID

from app.exceptions.errors import NotFoundError, ValidationError
from app.repositories.menu_category_repository import MenuCategoryRepository
from app.repositories.menu_item_repository import MenuItemRepository
from app.repositories.menu_repository import MenuRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.utils.list_envelope import list_envelope

logger = logging.getLogger(__name__)


def _get_menu_or_raise(restaurant_id: UUID, menu_id: UUID):
    if not RestaurantRepository.get_by_id(restaurant_id):
        raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
    menu = MenuRepository.get_by_id(restaurant_id, menu_id)
    if not menu:
        raise NotFoundError(f"Menu with id={menu_id} not found.")
    return menu


def _get_category_or_raise(menu_id: UUID, category_id: UUID):
    cat = MenuCategoryRepository.get_by_id(menu_id, category_id)
    if not cat:
        raise NotFoundError(f"Category with id={category_id} not found.")
    return cat


class MenuCategoryService:
    @staticmethod
    def get_all(restaurant_id: UUID, menu_id: UUID) -> dict:
        _get_menu_or_raise(restaurant_id, menu_id)
        cats = MenuCategoryRepository.get_all(menu_id)
        return list_envelope([c.to_dict() for c in cats])

    @staticmethod
    def create(
        restaurant_id: UUID, menu_id: UUID, name: str, display_order: int = 0
    ) -> dict:
        _get_menu_or_raise(restaurant_id, menu_id)
        name = (name or "").strip()
        if not name:
            raise ValidationError("Name is required.", {"name": "Cannot be empty"})
        cat = MenuCategoryRepository.create(menu_id, name, display_order)
        logger.info("MenuCategory created: menu_id=%s cat_id=%s", menu_id, cat.id)
        return cat.to_dict()

    @staticmethod
    def get_by_id(restaurant_id: UUID, menu_id: UUID, category_id: UUID) -> dict:
        _get_menu_or_raise(restaurant_id, menu_id)
        cat = _get_category_or_raise(menu_id, category_id)
        return cat.to_dict()

    @staticmethod
    def get_detail(restaurant_id: UUID, menu_id: UUID, category_id: UUID) -> dict:
        _get_menu_or_raise(restaurant_id, menu_id)
        cat = _get_category_or_raise(menu_id, category_id)
        return {
            **cat.to_dict(),
            "items": [i.to_dict() for i in MenuItemRepository.get_all(category_id)],
        }

    @staticmethod
    def update(
        restaurant_id: UUID,
        menu_id: UUID,
        category_id: UUID,
        name: str,
        display_order: int,
        is_active: bool,
    ) -> dict:
        _get_menu_or_raise(restaurant_id, menu_id)
        cat = _get_category_or_raise(menu_id, category_id)
        name = (name or "").strip()
        if not name:
            raise ValidationError("Name is required.", {"name": "Cannot be empty"})
        cat.name = name
        cat.display_order = display_order
        cat.is_active = is_active
        MenuCategoryRepository.save(cat)
        logger.info("MenuCategory updated: cat_id=%s", category_id)
        return cat.to_dict()

    @staticmethod
    def delete(restaurant_id: UUID, menu_id: UUID, category_id: UUID) -> None:
        _get_menu_or_raise(restaurant_id, menu_id)
        cat = _get_category_or_raise(menu_id, category_id)
        MenuCategoryRepository.delete(cat)
        logger.info("MenuCategory deleted: cat_id=%s", category_id)

    @staticmethod
    def reorder(restaurant_id: UUID, menu_id: UUID, ordered_ids: list[UUID]) -> dict:
        _get_menu_or_raise(restaurant_id, menu_id)
        existing = MenuCategoryRepository.get_all(menu_id)
        existing_ids = {c.id for c in existing}
        for oid in ordered_ids:
            if oid not in existing_ids:
                raise ValidationError(
                    f"Category id={oid} does not belong to menu id={menu_id}.",
                    {"orderedIds": f"Unknown id {oid}"},
                )
        MenuCategoryRepository.bulk_reorder(ordered_ids)
        cats = MenuCategoryRepository.get_all(menu_id)
        logger.info("MenuCategories reordered: menu_id=%s", menu_id)
        return list_envelope([c.to_dict() for c in cats])
