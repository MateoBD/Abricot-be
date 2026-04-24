import logging
from decimal import Decimal, InvalidOperation
from uuid import UUID

from app.exceptions.errors import NotFoundError, ValidationError
from app.integrations.s3 import S3Client
from app.repositories.menu_category_repository import MenuCategoryRepository
from app.repositories.menu_item_repository import MenuItemRepository

logger = logging.getLogger(__name__)

_ALLOWED_PHOTO_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _parse_price(value) -> Decimal:
    try:
        price = Decimal(str(value))
    except (InvalidOperation, TypeError) as err:
        raise ValidationError("Invalid price.", {"price": "Must be a valid number"}) from err
    if price < Decimal("0"):
        raise ValidationError("Price must be non-negative.", {"price": "Must be >= 0"})
    return price


class MenuItemService:
    @staticmethod
    def get_all(category_id: UUID) -> list[dict]:
        items = MenuItemRepository.get_all(category_id)
        return [i.to_dict() for i in items]

    @staticmethod
    def get_by_id(item_id: UUID) -> dict:
        item = MenuItemRepository.get_by_id(item_id)
        if not item:
            raise NotFoundError(f"Menu item with id={item_id} not found.")
        return item.to_dict()

    @staticmethod
    def create(
        category_id: UUID,
        name: str,
        description: str | None,
        price,
        is_available: bool = True,
    ) -> dict:
        if not MenuCategoryRepository.get_by_category_id(category_id):
            raise NotFoundError(f"Category with id={category_id} not found.")
        name = (name or "").strip()
        if not name:
            raise ValidationError("Name is required.", {"name": "Cannot be empty"})
        parsed_price = _parse_price(price)
        item = MenuItemRepository.create(
            category_id=category_id,
            name=name,
            description=(description or "").strip() or None,
            price=parsed_price,
            is_available=is_available,
        )
        logger.info("MenuItem created: category_id=%s item_id=%s", category_id, item.id)
        return item.to_dict()

    @staticmethod
    def update(
        item_id: UUID,
        name: str,
        description: str | None,
        price,
        is_available: bool,
    ) -> dict:
        item = MenuItemRepository.get_by_id(item_id)
        if not item:
            raise NotFoundError(f"Menu item with id={item_id} not found.")
        name = (name or "").strip()
        if not name:
            raise ValidationError("Name is required.", {"name": "Cannot be empty"})
        item.name = name
        item.description = (description or "").strip() or None
        item.price = _parse_price(price)
        item.is_available = is_available
        MenuItemRepository.save(item)
        logger.info("MenuItem updated: item_id=%s", item_id)
        return item.to_dict()

    @staticmethod
    def delete(item_id: UUID) -> None:
        item = MenuItemRepository.get_by_id(item_id)
        if not item:
            raise NotFoundError(f"Menu item with id={item_id} not found.")
        MenuItemRepository.delete(item)
        logger.info("MenuItem deleted: item_id=%s", item_id)

    @staticmethod
    def upload_photo(item_id: UUID, file_storage) -> dict:
        if not file_storage:
            raise ValidationError("No file provided.", {"file": "Missing file"})
        mime_type = (getattr(file_storage, "mimetype", None) or "").lower()
        if mime_type not in _ALLOWED_PHOTO_MIME_TYPES:
            raise ValidationError(
                "Invalid file format.",
                {"file": "Allowed types: image/jpeg, image/png, image/webp"},
            )
        item = MenuItemRepository.get_by_id(item_id)
        if not item:
            raise NotFoundError(f"Menu item with id={item_id} not found.")
        url = S3Client.get().upload_menu_item_photo(file_storage, item_id)
        item.photo_url = url
        MenuItemRepository.save(item)
        logger.info("MenuItem photo uploaded: item_id=%s", item_id)
        return item.to_dict()

    @staticmethod
    def set_availability(item_id: UUID, is_available: bool) -> dict:
        item = MenuItemRepository.get_by_id(item_id)
        if not item:
            raise NotFoundError(f"Menu item with id={item_id} not found.")
        item.is_available = is_available
        MenuItemRepository.save(item)
        logger.info("MenuItem availability set: item_id=%s is_available=%s", item_id, is_available)
        return item.to_dict()
