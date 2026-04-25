import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

from app.exceptions.errors import NotFoundError, ValidationError
from app.models.enums import DiscountType
from app.models.promotion import PromotionModel
from app.repositories.menu_item_repository import MenuItemRepository
from app.repositories.promotion_item_repository import PromotionItemRepository
from app.repositories.promotion_repository import PromotionRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.utils.list_envelope import list_envelope

logger = logging.getLogger(__name__)


def _parse_date(value: str | None, field: str) -> date:
    if not value:
        raise ValidationError(f"{field} is required.", {field: "Required"})
    try:
        return date.fromisoformat(value)
    except ValueError as err:
        raise ValidationError(
            f"Invalid {field}. Expected YYYY-MM-DD.", {field: "Invalid date format"}
        ) from err


def _parse_discount_value(value) -> Decimal:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError) as err:
        raise ValidationError("Invalid discountValue.", {"discountValue": "Must be a number"}) from err
    if d < Decimal("0"):
        raise ValidationError("discountValue must be non-negative.", {"discountValue": "Must be >= 0"})
    return d


def _parse_discount_type(value: str | None) -> DiscountType:
    try:
        return DiscountType(value)
    except (ValueError, TypeError) as err:
        raise ValidationError(
            "Invalid discountType.",
            {"discountType": "Must be PERCENTAGE, FIXED_AMOUNT, or FREE_ITEM"},
        ) from err


def _promo_payload(promo: PromotionModel, menu_item_ids: list[UUID] | None = None) -> dict:
    data = promo.to_dict()
    if menu_item_ids is not None:
        data["menuItemIds"] = [str(mid) for mid in menu_item_ids]
    return data


class PromotionService:
    @staticmethod
    def _get_restaurant_or_raise(restaurant_id: UUID):
        r = RestaurantRepository.get_by_id(restaurant_id)
        if not r:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        return r

    @staticmethod
    def _get_promo_or_raise(restaurant_id: UUID, promotion_id: UUID) -> PromotionModel:
        promo = PromotionRepository.get_by_id(restaurant_id, promotion_id)
        if not promo:
            raise NotFoundError(f"Promotion with id={promotion_id} not found.")
        return promo

    @staticmethod
    def get_all_active(restaurant_id: UUID) -> dict:
        PromotionService._get_restaurant_or_raise(restaurant_id)
        promos = PromotionRepository.get_active(restaurant_id)
        return list_envelope([p.to_dict() for p in promos])

    @staticmethod
    def get_all_for_admin(restaurant_id: UUID) -> dict:
        PromotionService._get_restaurant_or_raise(restaurant_id)
        promos = PromotionRepository.get_all(restaurant_id)
        data: list[dict] = []
        for p in promos:
            data.append(
                _promo_payload(p, PromotionItemRepository.list_menu_item_ids(p.id))
            )
        return list_envelope(data)

    @staticmethod
    def get_feed() -> dict:
        promos = PromotionRepository.get_global_feed()
        return list_envelope([p.to_dict() for p in promos])

    @staticmethod
    def get_by_id(restaurant_id: UUID, promotion_id: UUID) -> dict:
        PromotionService._get_restaurant_or_raise(restaurant_id)
        promo = PromotionService._get_promo_or_raise(restaurant_id, promotion_id)
        item_ids = PromotionItemRepository.list_menu_item_ids(promo.id)
        return _promo_payload(promo, item_ids)

    @staticmethod
    def create(
        restaurant_id: UUID,
        title: str,
        description: str | None,
        discount_type: str,
        discount_value,
        start_date: str,
        end_date: str,
        notify_users: bool = False,
        menu_item_ids: list | None = None,
    ) -> dict:
        PromotionService._get_restaurant_or_raise(restaurant_id)
        title = (title or "").strip()
        if not title:
            raise ValidationError("title is required.", {"title": "Cannot be empty"})

        dtype = _parse_discount_type(discount_type)
        dvalue = _parse_discount_value(discount_value)
        sdate = _parse_date(start_date, "startDate")
        edate = _parse_date(end_date, "endDate")
        if sdate > edate:
            raise ValidationError(
                "startDate must be before or equal to endDate.",
                {"startDate": "Must be <= endDate"},
            )

        promo = PromotionModel(
            restaurant_id=restaurant_id,
            title=title,
            description=(description or "").strip() or None,
            discount_type=dtype,
            discount_value=dvalue,
            start_date=sdate,
            end_date=edate,
            is_active=True,
            notify_users=notify_users,
        )
        PromotionRepository.create(promo)

        item_uuids = _parse_item_ids(menu_item_ids, restaurant_id)
        if item_uuids:
            PromotionItemRepository.replace_items(promo.id, item_uuids)

        if notify_users:
            _try_notify_promotion(promo.id)

        logger.info("Promotion created: restaurant_id=%s promo_id=%s", restaurant_id, promo.id)
        return _promo_payload(promo, item_uuids)

    @staticmethod
    def update(
        restaurant_id: UUID,
        promotion_id: UUID,
        title: str,
        description: str | None,
        discount_type: str,
        discount_value,
        start_date: str,
        end_date: str,
        notify_users: bool = False,
        menu_item_ids: list | None = None,
    ) -> dict:
        PromotionService._get_restaurant_or_raise(restaurant_id)
        promo = PromotionService._get_promo_or_raise(restaurant_id, promotion_id)

        title = (title or "").strip()
        if not title:
            raise ValidationError("title is required.", {"title": "Cannot be empty"})

        promo.title = title
        promo.description = (description or "").strip() or None
        promo.discount_type = _parse_discount_type(discount_type)
        promo.discount_value = _parse_discount_value(discount_value)
        promo.start_date = _parse_date(start_date, "startDate")
        promo.end_date = _parse_date(end_date, "endDate")
        if promo.start_date > promo.end_date:
            raise ValidationError(
                "startDate must be before or equal to endDate.",
                {"startDate": "Must be <= endDate"},
            )
        promo.notify_users = notify_users
        PromotionRepository.save(promo)

        item_uuids = _parse_item_ids(menu_item_ids, restaurant_id)
        PromotionItemRepository.replace_items(promo.id, item_uuids)

        logger.info("Promotion updated: promo_id=%s", promotion_id)
        return promo.to_dict()

    @staticmethod
    def deactivate(restaurant_id: UUID, promotion_id: UUID) -> dict:
        PromotionService._get_restaurant_or_raise(restaurant_id)
        promo = PromotionService._get_promo_or_raise(restaurant_id, promotion_id)
        promo.is_active = False
        PromotionRepository.save(promo)
        logger.info("Promotion deactivated: promo_id=%s", promotion_id)
        return promo.to_dict()

    @staticmethod
    def activate(restaurant_id: UUID, promotion_id: UUID) -> dict:
        PromotionService._get_restaurant_or_raise(restaurant_id)
        promo = PromotionService._get_promo_or_raise(restaurant_id, promotion_id)
        promo.is_active = True
        PromotionRepository.save(promo)
        logger.info("Promotion activated: promo_id=%s", promotion_id)
        return promo.to_dict()

    @staticmethod
    def delete(restaurant_id: UUID, promotion_id: UUID) -> None:
        PromotionService._get_restaurant_or_raise(restaurant_id)
        promo = PromotionService._get_promo_or_raise(restaurant_id, promotion_id)
        PromotionRepository.delete(promo)
        logger.info("Promotion deleted: promo_id=%s", promotion_id)


def _parse_item_ids(menu_item_ids: list | None, restaurant_id: UUID) -> list[UUID]:
    if not menu_item_ids:
        return []
    ids: list[UUID] = []
    for raw in menu_item_ids:
        try:
            ids.append(UUID(str(raw)))
        except ValueError as err:
            raise ValidationError(
                f"Invalid menu item id: {raw}", {"menuItemIds": "Must be valid UUIDs"}
            ) from err
    if not MenuItemRepository.validate_items_for_restaurant(ids, restaurant_id):
        raise ValidationError(
            "One or more menu items do not belong to this restaurant.",
            {"menuItemIds": "Invalid items"},
        )
    return ids


def _try_notify_promotion(promotion_id: UUID) -> None:
    try:
        from app.services.notification_service import NotificationService
        NotificationService.send_promotion_notification(promotion_id)
    except Exception:
        logger.warning("Failed to send promotion notification for promo_id=%s", promotion_id)
