from uuid import UUID

from app.exceptions.errors import (
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.models.enums import UserRole
from app.models.order import OrderModel
from app.models.user import UserModel
from app.repositories.order_repository import OrderRepository
from app.repositories.restaurant_admin_repository import RestaurantAdminRepository
from app.repositories.user_repository import UserRepository
from app.services.order_event_publisher import publish_order_created
from app.services.order_service import OrderService
from app.services.user_service import UserService


def _parse_uuid(value: str | UUID | None, field: str) -> UUID:
    if value is None or value == "":
        raise ValidationError(f"{field} is required.", {field: "Required"})
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError as error:
        raise ValidationError("Invalid identifier format.", {field: "Invalid UUID"}) from error


class CognitoOrderService:
    @staticmethod
    def create_order(
        *,
        restaurant_id: str | UUID,
        cognito_sub: str | None,
        body: dict,
    ) -> dict:
        principal = CognitoOrderService._principal_user(cognito_sub)
        order = OrderService.create(
            restaurant_id=_parse_uuid(restaurant_id, "restaurantId"),
            user_id=principal.id,
            items=body.get("items") or [],
            notes=body.get("notes"),
        )
        publish_order_created(order)
        return order

    @staticmethod
    def list_user_orders(
        *,
        user_id: str | UUID,
        cognito_sub: str | None,
        is_cognito_admin: bool = False,
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        target_id = _parse_uuid(user_id, "userId")
        principal = CognitoOrderService._principal_user(cognito_sub)
        CognitoOrderService._require_same_user_or_super_admin(
            principal=principal,
            target_id=target_id,
            is_cognito_admin=is_cognito_admin,
        )
        return UserService.get_my_orders(target_id, page=page, per_page=per_page)

    @staticmethod
    def list_restaurant_orders(
        *,
        restaurant_id: str | UUID,
        cognito_sub: str | None,
        is_cognito_admin: bool = False,
        status_filter: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        restaurant_uuid = _parse_uuid(restaurant_id, "restaurantId")
        principal = CognitoOrderService._principal_user(cognito_sub)
        CognitoOrderService._require_restaurant_admin(
            principal=principal,
            restaurant_id=restaurant_uuid,
            is_cognito_admin=is_cognito_admin,
        )
        return OrderService.list_for_restaurant(
            restaurant_id=restaurant_uuid,
            status_filter=status_filter,
            page=page,
            per_page=per_page,
        )

    @staticmethod
    def get_restaurant_order(
        *,
        restaurant_id: str | UUID,
        order_id: str | UUID,
        cognito_sub: str | None,
        is_cognito_admin: bool = False,
    ) -> dict:
        restaurant_uuid = _parse_uuid(restaurant_id, "restaurantId")
        order_uuid = _parse_uuid(order_id, "orderId")
        principal = CognitoOrderService._principal_user(cognito_sub)
        order = CognitoOrderService._order_for_restaurant(order_uuid, restaurant_uuid)

        if CognitoOrderService._can_access_order(
            principal=principal,
            order=order,
            is_cognito_admin=is_cognito_admin,
        ):
            if (
                principal.role == UserRole.SUPER_ADMIN
                or is_cognito_admin
                or order.user_id != principal.id
            ):
                return OrderService.get_by_id_for_restaurant_admin(
                    order_uuid,
                    restaurant_uuid,
                )
            return OrderService.get_by_id(order_uuid, principal.id)

        raise ForbiddenError("Forbidden.", public_message="Forbidden.")

    @staticmethod
    def patch_restaurant_order(
        *,
        restaurant_id: str | UUID,
        order_id: str | UUID,
        cognito_sub: str | None,
        body: dict,
        is_cognito_admin: bool = False,
    ) -> dict:
        restaurant_uuid = _parse_uuid(restaurant_id, "restaurantId")
        order_uuid = _parse_uuid(order_id, "orderId")
        principal = CognitoOrderService._principal_user(cognito_sub)
        CognitoOrderService._require_restaurant_admin(
            principal=principal,
            restaurant_id=restaurant_uuid,
            is_cognito_admin=is_cognito_admin,
        )
        requested_status = str(body.get("status", "")).strip().upper()
        if requested_status == "CANCELLED":
            return OrderService.cancel(
                order_uuid,
                principal.id,
                restaurant_id=restaurant_uuid,
                is_super_admin=principal.role == UserRole.SUPER_ADMIN or is_cognito_admin,
            )

        return OrderService.update_status(
            order_id=order_uuid,
            new_status_str=requested_status,
            estimated_ready_at=body.get("estimatedReadyAt"),
            restaurant_id=restaurant_uuid,
        )

    @staticmethod
    def _principal_user(cognito_sub: str | None) -> UserModel:
        cognito_sub = (cognito_sub or "").strip()
        if not cognito_sub:
            raise UnauthorizedError(
                "Missing Cognito sub claim.",
                public_message="Missing Cognito sub claim.",
            )
        user = UserRepository.get_by_cognito_sub(cognito_sub)
        if not user:
            raise UnauthorizedError(
                "Local user is not linked to this Cognito identity.",
                public_message="Local user is not linked to this Cognito identity.",
            )
        return user

    @staticmethod
    def _require_same_user_or_super_admin(
        *,
        principal: UserModel,
        target_id: UUID,
        is_cognito_admin: bool,
    ) -> None:
        if (
            principal.id == target_id
            or principal.role == UserRole.SUPER_ADMIN
            or is_cognito_admin
        ):
            return
        raise ForbiddenError("Forbidden.", public_message="Forbidden.")

    @staticmethod
    def _require_restaurant_admin(
        *,
        principal: UserModel,
        restaurant_id: UUID,
        is_cognito_admin: bool,
    ) -> None:
        if principal.role == UserRole.SUPER_ADMIN or is_cognito_admin:
            return

        if principal.role != UserRole.RESTAURANT_ADMIN:
            raise ForbiddenError("Forbidden.", public_message="Forbidden.")

        if not RestaurantAdminRepository.is_admin(
            user_id=principal.id,
            restaurant_id=restaurant_id,
        ):
            raise ForbiddenError("Forbidden.", public_message="Forbidden.")

    @staticmethod
    def _order_for_restaurant(order_id: UUID, restaurant_id: UUID) -> OrderModel:
        order = OrderRepository.get_by_id(order_id)
        if not order or order.restaurant_id != restaurant_id:
            raise NotFoundError("Order not found.", public_message="Order not found.")
        return order

    @staticmethod
    def _can_access_order(
        *,
        principal: UserModel,
        order: OrderModel,
        is_cognito_admin: bool,
    ) -> bool:
        if principal.id == order.user_id:
            return True
        if principal.role == UserRole.SUPER_ADMIN or is_cognito_admin:
            return True
        if principal.role != UserRole.RESTAURANT_ADMIN:
            return False
        return RestaurantAdminRepository.is_admin(
            user_id=principal.id,
            restaurant_id=order.restaurant_id,
        )
