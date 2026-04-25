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
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.IN_PREPARATION, OrderStatus.CANCELLED},
    OrderStatus.IN_PREPARATION: {OrderStatus.READY},
    OrderStatus.READY: {OrderStatus.COMPLETED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}


def _order_payload(order: OrderModel, include_items: bool = False) -> dict:
    data = order.to_dict()
    if include_items:
        items = OrderItemRepository.get_by_order(order.id)
        data["items"] = [i.to_dict() for i in items]
    return data


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
            raise ConflictError("No active menu found for this restaurant.")

        total = Decimal("0")
        order_items: list[dict] = []
        for entry in items:
            item_id = entry.get("menuItemId")
            qty = entry.get("quantity", 1)
            item_notes = entry.get("notes")

            if not item_id:
                raise ValidationError("Each item must have a menuItemId.", {"menuItemId": "Required"})
            if not isinstance(qty, int) or qty < 1:
                raise ValidationError("quantity must be a positive integer.", {"quantity": "Must be >= 1"})

            menu_item = MenuItemRepository.get_by_id(UUID(str(item_id)))
            if not menu_item or not menu_item.is_available:
                raise ValidationError(
                    f"Menu item {item_id} is not available.",
                    {"menuItemId": f"{item_id} not available"},
                )
            if not MenuItemRepository.validate_items_for_restaurant([menu_item.id], restaurant_id):
                raise ValidationError(
                    f"Menu item {item_id} does not belong to this restaurant.",
                    {"menuItemId": f"{item_id} invalid"},
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
            notes=notes,
        )
        OrderRepository.create(order)
        saved_items = OrderItemRepository.bulk_insert(order.id, order_items)
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
    def cancel(order_id: UUID, requesting_user_id: UUID) -> dict:
        order = OrderRepository.get_by_id(order_id)
        if not order:
            raise NotFoundError(f"Order with id={order_id} not found.")
        if order.status != OrderStatus.PENDING:
            raise ConflictError(
                f"Only orders in PENDING status can be cancelled. Current: '{order.status.value}'."
            )
        if order.user_id != requesting_user_id:
            from app.repositories.restaurant_admin_repository import RestaurantAdminRepository
            if not RestaurantAdminRepository.is_admin(
                user_id=requesting_user_id, restaurant_id=order.restaurant_id
            ):
                raise ForbiddenError("You do not have permission to cancel this order.")

        OrderRepository.update_status(order, OrderStatus.CANCELLED)
        logger.info("Order cancelled: order_id=%s by_user=%s", order_id, requesting_user_id)
        return _order_payload(order)
