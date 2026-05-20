import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.exceptions.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.enums import OrderStatus
from app.models.order import OrderModel
from app.repositories.menu_item_repository import MenuItemRepository
from app.repositories.menu_repository import MenuRepository
from app.repositories.order_item_repository import OrderItemRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.utils.list_envelope import paginated_list_envelope

logger = logging.getLogger(__name__)

_VALID_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED},
    OrderStatus.CONFIRMED: {OrderStatus.READY},
    OrderStatus.READY: {OrderStatus.COMPLETED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}


def _parse_item_uuid(value: str | UUID | None) -> UUID:
    if value is None or value == "":
        raise ValidationError("Each item must have a menuItemId.", {"menuItemId": "Required"})
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError as err:
        raise ValidationError("Invalid identifier format.", {"menuItemId": "Invalid UUID"}) from err


def _order_payload(order: OrderModel, include_items: bool = False) -> dict:
    data = order.to_dict()
    if include_items:
        items = OrderItemRepository.get_by_order(order.id)
        data["items"] = [i.to_dict() for i in items]
    return data


def _parse_item_quantity(value) -> int:
    if not isinstance(value, int) or value < 1:
        raise ValidationError("quantity must be a positive integer.", {"quantity": "Must be >= 1"})
    return value


def _normalize_item_notes(value) -> str | None:
    if value is None:
        return None
    notes = str(value).strip()
    if not notes:
        return None
    if len(notes) > 500:
        raise ValidationError("Item notes exceed the maximum length.", {"notes": "Max length is 500"})
    return notes


class OrderService:
    @staticmethod
    def create(
        restaurant_id: UUID,
        user_id: UUID,
        items: list[dict],
        notes: str | None = None,
    ) -> dict:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        if not items:
            raise ValidationError("At least one item is required.", {"items": "Cannot be empty"})

        active_menu = MenuRepository.get_active(restaurant_id)
        if not active_menu:
            raise NotFoundError("Restaurant has no active menu.")

        parsed_items: list[tuple[UUID, int, str | None]] = []
        requested_item_ids: list[UUID] = []
        for entry in items:
            if not isinstance(entry, dict):
                raise ValidationError(
                    "Each item must be a JSON object.",
                    {"items": "Invalid item payload"},
                )
            item_id = _parse_item_uuid(entry.get("menuItemId"))
            qty = _parse_item_quantity(entry.get("quantity", 1))
            item_notes = _normalize_item_notes(entry.get("notes"))

            parsed_items.append((item_id, qty, item_notes))
            requested_item_ids.append(item_id)

        requested_unique = list(dict.fromkeys(requested_item_ids))
        available_items = MenuItemRepository.get_available_for_menu(
            requested_unique,
            active_menu.id,
        )
        menu_items = {item.id: item for item in available_items}

        missing_or_unavailable = [
            str(item_id) for item_id in requested_unique if item_id not in menu_items
        ]
        if missing_or_unavailable:
            raise ValidationError(
                "Each menu item must exist, be available, and belong to the active menu.",
                {
                    "items": "Contains invalid or unavailable menu items",
                    "menuItemIds": missing_or_unavailable,
                },
            )

        total = Decimal("0")
        order_items: list[dict] = []
        for item_id, qty, item_notes in parsed_items:
            menu_item = menu_items.get(item_id)
            if not menu_item or not menu_item.is_available:
                raise ValidationError(
                    f"Menu item {item_id} is not available.",
                    {"menuItemId": f"{item_id} not available"},
                )

            snapshot_price = menu_item.price
            total += snapshot_price * qty
            order_items.append(
                {
                    "menu_item_id": menu_item.id,
                    "quantity": qty,
                    "unit_price": snapshot_price,
                    "notes": item_notes,
                }
            )

        order = OrderModel(
            restaurant_id=restaurant_id,
            user_id=user_id,
            status=OrderStatus.PENDING,
            total_amount=total,
            notes=(notes or "").strip() or None,
        )
        _, saved_items = OrderRepository.create_with_items(order, order_items)
        logger.info("Order created: order_id=%s user_id=%s total=%s", order.id, user_id, total)
        return {**order.to_dict(), "items": [i.to_dict() for i in saved_items]}

    @staticmethod
    def get_by_id(order_id: UUID, requesting_user_id: UUID) -> dict:
        order = OrderRepository.get_by_id(order_id)
        if not order:
            raise NotFoundError(f"Order with id={order_id} not found.")
        if order.user_id != requesting_user_id:
            from app.repositories.restaurant_admin_repository import RestaurantAdminRepository
            if not RestaurantAdminRepository.is_admin(
                user_id=requesting_user_id, restaurant_id=order.restaurant_id
            ):
                raise ForbiddenError("You do not have access to this order.")
        return _order_payload(order, include_items=True)

    @staticmethod
    def list_for_restaurant(
        restaurant_id: UUID,
        status_filter: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")

        status = None
        if status_filter:
            try:
                status = OrderStatus(status_filter)
            except ValueError as err:
                raise ValidationError(
                    "Invalid status.", {"status": "Must be a valid OrderStatus"}
                ) from err

        rows, total = OrderRepository.list_for_restaurant(
            restaurant_id=restaurant_id,
            filters={"status": status} if status else None,
            page=page,
            per_page=per_page,
        )
        return paginated_list_envelope(
            [_order_payload(r) for r in rows], total=total, page=page, per_page=per_page
        )

    @staticmethod
    def update_status(
        order_id: UUID,
        new_status_str: str,
        estimated_ready_at: str | None = None,
        *,
        restaurant_id: UUID | None = None,
    ) -> dict:
        order = OrderRepository.get_by_id(order_id)
        if not order:
            raise NotFoundError(f"Order with id={order_id} not found.")
        if restaurant_id is not None and order.restaurant_id != restaurant_id:
            raise NotFoundError(f"Order with id={order_id} not found.")

        if not (new_status_str and str(new_status_str).strip()):
            raise ValidationError(
                "Status is required.",
                {"status": "Required"},
            )

        try:
            new_status = OrderStatus(new_status_str.strip().upper())
        except ValueError as err:
            raise ValidationError(
                "Invalid status.", {"status": "Must be a valid OrderStatus"}
            ) from err

        if new_status not in _VALID_TRANSITIONS.get(order.status, set()):
            raise ConflictError(
                f"Cannot transition from '{order.status.value}' to '{new_status.value}'.",
                {"status": "Invalid transition"},
            )

        parsed_eta: datetime | None = None
        if estimated_ready_at is not None and str(estimated_ready_at).strip() != "":
            try:
                parsed_eta = datetime.fromisoformat(str(estimated_ready_at).strip())
            except ValueError as err:
                raise ValidationError(
                    "Invalid estimatedReadyAt. Expected ISO 8601.",
                    {"estimatedReadyAt": "Invalid datetime format"},
                ) from err

        OrderRepository.update_status(order, new_status, parsed_eta)
        logger.info("Order status updated: order_id=%s new_status=%s", order_id, new_status)
        return _order_payload(order, include_items=restaurant_id is not None)

    @staticmethod
    def get_by_id_for_restaurant_admin(
        order_id: UUID,
        restaurant_id: UUID,
    ) -> dict:
        order = OrderRepository.get_by_id(order_id)
        if not order:
            raise NotFoundError(f"Order with id={order_id} not found.")
        if order.restaurant_id != restaurant_id:
            raise NotFoundError(f"Order with id={order_id} not found.")
        return _order_payload(order, include_items=True)

    @staticmethod
    def cancel(
        order_id: UUID,
        requesting_user_id: UUID,
        *,
        restaurant_id: UUID | None = None,
        is_super_admin: bool = False,
    ) -> dict:
        order = OrderRepository.get_by_id(order_id)
        if not order:
            raise NotFoundError(f"Order with id={order_id} not found.")
        if restaurant_id is not None and order.restaurant_id != restaurant_id:
            raise NotFoundError(f"Order with id={order_id} not found.")
        if order.status != OrderStatus.PENDING:
            raise ConflictError(
                f"Only orders in PENDING status can be cancelled. Current: '{order.status.value}'."
            )
        if order.user_id != requesting_user_id:
            from app.repositories.restaurant_admin_repository import RestaurantAdminRepository
            if not is_super_admin and not RestaurantAdminRepository.is_admin(
                user_id=requesting_user_id, restaurant_id=order.restaurant_id
            ):
                raise ForbiddenError("You do not have permission to cancel this order.")

        OrderRepository.update_status(order, OrderStatus.CANCELLED)
        logger.info("Order cancelled: order_id=%s by_user=%s", order_id, requesting_user_id)
        return _order_payload(order, include_items=restaurant_id is not None)
