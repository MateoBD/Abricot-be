from uuid import UUID

from app.exceptions.errors import UnauthorizedError, ValidationError
from app.models.user import UserModel
from app.repositories.user_repository import UserRepository
from app.services.availability_service import AvailabilityService
from app.services.business_hours_service import BusinessHoursService
from app.services.cognito_authorization_service import (
    CognitoAuthorizationService,
)
from app.services.menu_category_service import MenuCategoryService
from app.services.menu_item_service import MenuItemService
from app.services.menu_service import MenuService
from app.services.restaurant_admin_service import RestaurantAdminService
from app.services.restaurant_review_service import RestaurantReviewService
from app.services.restaurant_service import FIELD_UNSET, RestaurantService
from app.services.table_service import TableService

_PRIVILEGE_BODY_KEYS = frozenset(
    {"userId", "role", "creatorUserId", "adminUserId", "isAdmin"}
)


def _parse_uuid(value: str | UUID | None, field: str) -> UUID:
    if value is None or value == "":
        raise ValidationError(f"{field} is required.", {field: "Required"})
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError as error:
        raise ValidationError("Invalid identifier format.", {field: "Invalid UUID"}) from error


class CognitoRestaurantService:
    @staticmethod
    def reject_privilege_fields(data: dict) -> None:
        rejected = sorted(key for key in data if key in _PRIVILEGE_BODY_KEYS)
        if rejected:
            raise ValidationError(
                "Privilege fields are not allowed in this request.",
                {key: "Not allowed" for key in rejected},
            )

    @staticmethod
    def create_restaurant(*, cognito_sub: str | None, body: dict) -> dict:
        CognitoRestaurantService.reject_privilege_fields(body)
        principal = CognitoRestaurantService._principal_user(cognito_sub)
        return RestaurantService.create(
            name=body.get("name", ""),
            address=body.get("address", ""),
            phone=body.get("phone", ""),
            city_id=body.get("cityId"),
            email=body.get("email"),
            description=body.get("description"),
            neighbourhood_id=body.get("neighbourhoodId"),
            price_range_id=body.get("priceRangeId"),
            cuisine_type_ids=body.get("cuisineTypeIds"),
            creator_user_id=principal.id,
        )

    @staticmethod
    def update_restaurant(
        *,
        restaurant_id: str | UUID,
        cognito_sub: str | None,
        body: dict,
        is_cognito_admin: bool = False,
    ) -> dict:
        CognitoAuthorizationService.reject_privilege_fields(body)
        restaurant_uuid = _parse_uuid(restaurant_id, "restaurantId")
        principal = CognitoAuthorizationService.principal_user(cognito_sub)
        CognitoAuthorizationService.require_restaurant_admin(
            principal=principal,
            restaurant_id=restaurant_uuid,
            is_cognito_admin=is_cognito_admin,
        )
        return RestaurantService.update(
            restaurant_id=restaurant_uuid,
            name=body.get("name", ""),
            address=body.get("address", ""),
            phone=body.get("phone", ""),
            email=body.get("email"),
            description=body.get("description"),
            city_id=body.get("cityId"),
            neighbourhood_id=body["neighbourhoodId"]
            if "neighbourhoodId" in body
            else FIELD_UNSET,
            price_range_id=body["priceRangeId"]
            if "priceRangeId" in body
            else FIELD_UNSET,
            cuisine_type_ids=body["cuisineTypeIds"]
            if "cuisineTypeIds" in body
            else FIELD_UNSET,
        )

    @staticmethod
    def delete_restaurant(
        *,
        restaurant_id: str | UUID,
        cognito_sub: str | None,
        is_cognito_admin: bool = False,
    ) -> None:
        restaurant_uuid = _parse_uuid(restaurant_id, "restaurantId")
        principal = CognitoAuthorizationService.principal_user(cognito_sub)
        CognitoAuthorizationService.require_restaurant_admin(
            principal=principal,
            restaurant_id=restaurant_uuid,
            is_cognito_admin=is_cognito_admin,
        )
        RestaurantService.delete(restaurant_uuid)

    @staticmethod
    def put_review(
        *,
        restaurant_id: str | UUID,
        user_id: str | UUID,
        cognito_sub: str | None,
        body: dict,
        is_cognito_admin: bool = False,
    ) -> dict:
        restaurant_uuid = _parse_uuid(restaurant_id, "restaurantId")
        target_user_id = _parse_uuid(user_id, "userId")
        principal = CognitoAuthorizationService.principal_user(cognito_sub)
        CognitoAuthorizationService.require_same_user_or_super_admin(
            principal=principal,
            target_user_id=target_user_id,
            is_cognito_admin=is_cognito_admin,
        )
        return RestaurantReviewService.set_my_review(
            target_user_id,
            restaurant_uuid,
            body.get("score"),
        )

    @staticmethod
    def list_admins(
        *,
        restaurant_id: str | UUID,
        cognito_sub: str | None,
        is_cognito_admin: bool = False,
    ) -> dict:
        restaurant_uuid = _parse_uuid(restaurant_id, "restaurantId")
        principal = CognitoAuthorizationService.principal_user(cognito_sub)
        CognitoAuthorizationService.require_restaurant_admin(
            principal=principal,
            restaurant_id=restaurant_uuid,
            is_cognito_admin=is_cognito_admin,
        )
        result = RestaurantAdminService.list_admins(restaurant_uuid)
        return {
            **result,
            "data": [
                _strip_cognito_sub(row)
                for row in result.get("data", [])
            ],
        }

    @staticmethod
    def add_admin(
        *,
        restaurant_id: str | UUID,
        cognito_sub: str | None,
        body: dict,
        is_cognito_admin: bool = False,
    ) -> dict:
        CognitoAuthorizationService.reject_privilege_fields(body, allow_user_id=True)
        restaurant_uuid = _parse_uuid(restaurant_id, "restaurantId")
        principal = CognitoAuthorizationService.principal_user(cognito_sub)
        CognitoAuthorizationService.require_restaurant_admin(
            principal=principal,
            restaurant_id=restaurant_uuid,
            is_cognito_admin=is_cognito_admin,
        )
        return _strip_cognito_sub(
            RestaurantAdminService.add_admin(
                restaurant_uuid,
                body.get("userId"),
            )
        )

    @staticmethod
    def remove_admin(
        *,
        restaurant_id: str | UUID,
        user_id: str | UUID,
        cognito_sub: str | None,
        is_cognito_admin: bool = False,
    ) -> None:
        restaurant_uuid = _parse_uuid(restaurant_id, "restaurantId")
        target_user_id = _parse_uuid(user_id, "userId")
        principal = CognitoAuthorizationService.principal_user(cognito_sub)
        CognitoAuthorizationService.require_restaurant_admin(
            principal=principal,
            restaurant_id=restaurant_uuid,
            is_cognito_admin=is_cognito_admin,
        )
        RestaurantAdminService.remove_admin(restaurant_uuid, target_user_id)

    @staticmethod
    def list_admin_menus(*, restaurant_id: str | UUID, **auth) -> dict:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        return MenuService.get_all(restaurant_uuid)

    @staticmethod
    def create_admin_menu(*, restaurant_id: str | UUID, body: dict, **auth) -> dict:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        return MenuService.create(restaurant_uuid, body.get("name"))

    @staticmethod
    def get_admin_menu(*, restaurant_id: str | UUID, menu_id: str | UUID, **auth) -> dict:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        return MenuService.get_detail(restaurant_uuid, _parse_uuid(menu_id, "menuId"))

    @staticmethod
    def update_admin_menu(
        *,
        restaurant_id: str | UUID,
        menu_id: str | UUID,
        body: dict,
        **auth,
    ) -> dict:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        return MenuService.update(
            restaurant_uuid,
            _parse_uuid(menu_id, "menuId"),
            body.get("name"),
        )

    @staticmethod
    def patch_admin_menu(
        *,
        restaurant_id: str | UUID,
        menu_id: str | UUID,
        body: dict,
        **auth,
    ) -> dict:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        menu_uuid = _parse_uuid(menu_id, "menuId")
        if "isActive" not in body:
            raise ValidationError("isActive is required.", {"isActive": "Required"})
        if body.get("isActive"):
            return MenuService.activate(restaurant_uuid, menu_uuid)
        return MenuService.deactivate(restaurant_uuid, menu_uuid)

    @staticmethod
    def delete_admin_menu(*, restaurant_id: str | UUID, menu_id: str | UUID, **auth) -> None:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        MenuService.delete(restaurant_uuid, _parse_uuid(menu_id, "menuId"))

    @staticmethod
    def list_menu_categories(*, restaurant_id: str | UUID, menu_id: str | UUID, **auth) -> dict:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        return MenuCategoryService.get_all(restaurant_uuid, _parse_uuid(menu_id, "menuId"))

    @staticmethod
    def create_menu_category(
        *,
        restaurant_id: str | UUID,
        menu_id: str | UUID,
        body: dict,
        **auth,
    ) -> dict:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        return MenuCategoryService.create(
            restaurant_uuid,
            _parse_uuid(menu_id, "menuId"),
            body.get("name"),
            body.get("displayOrder", 0),
        )

    @staticmethod
    def get_menu_category(
        *,
        restaurant_id: str | UUID,
        menu_id: str | UUID,
        category_id: str | UUID,
        **auth,
    ) -> dict:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        return MenuCategoryService.get_detail(
            restaurant_uuid,
            _parse_uuid(menu_id, "menuId"),
            _parse_uuid(category_id, "categoryId"),
        )

    @staticmethod
    def update_menu_category(
        *,
        restaurant_id: str | UUID,
        menu_id: str | UUID,
        category_id: str | UUID,
        body: dict,
        **auth,
    ) -> dict:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        return MenuCategoryService.update(
            restaurant_uuid,
            _parse_uuid(menu_id, "menuId"),
            _parse_uuid(category_id, "categoryId"),
            body.get("name"),
            body.get("displayOrder", 0),
            body.get("isActive", True),
        )

    @staticmethod
    def delete_menu_category(
        *,
        restaurant_id: str | UUID,
        menu_id: str | UUID,
        category_id: str | UUID,
        **auth,
    ) -> None:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        MenuCategoryService.delete(
            restaurant_uuid,
            _parse_uuid(menu_id, "menuId"),
            _parse_uuid(category_id, "categoryId"),
        )

    @staticmethod
    def list_menu_items(
        *,
        restaurant_id: str | UUID,
        menu_id: str | UUID,
        category_id: str | UUID,
        **auth,
    ) -> dict:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        return MenuItemService.get_all_for_category(
            restaurant_uuid,
            _parse_uuid(menu_id, "menuId"),
            _parse_uuid(category_id, "categoryId"),
        )

    @staticmethod
    def create_menu_item(
        *,
        restaurant_id: str | UUID,
        menu_id: str | UUID,
        category_id: str | UUID,
        body: dict,
        **auth,
    ) -> dict:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        return MenuItemService.create_for_category(
            restaurant_uuid,
            _parse_uuid(menu_id, "menuId"),
            _parse_uuid(category_id, "categoryId"),
            body.get("name"),
            body.get("description"),
            body.get("price"),
            body.get("isAvailable", True),
        )

    @staticmethod
    def get_menu_item(
        *,
        restaurant_id: str | UUID,
        menu_id: str | UUID,
        category_id: str | UUID,
        item_id: str | UUID,
        **auth,
    ) -> dict:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        return MenuItemService.get_by_id_for_category(
            restaurant_uuid,
            _parse_uuid(menu_id, "menuId"),
            _parse_uuid(category_id, "categoryId"),
            _parse_uuid(item_id, "itemId"),
        )

    @staticmethod
    def update_menu_item(
        *,
        restaurant_id: str | UUID,
        menu_id: str | UUID,
        category_id: str | UUID,
        item_id: str | UUID,
        body: dict,
        **auth,
    ) -> dict:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        return MenuItemService.update_for_category(
            restaurant_uuid,
            _parse_uuid(menu_id, "menuId"),
            _parse_uuid(category_id, "categoryId"),
            _parse_uuid(item_id, "itemId"),
            body.get("name"),
            body.get("description"),
            body.get("price"),
            body.get("isAvailable", True),
        )

    @staticmethod
    def delete_menu_item(
        *,
        restaurant_id: str | UUID,
        menu_id: str | UUID,
        category_id: str | UUID,
        item_id: str | UUID,
        **auth,
    ) -> None:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        MenuItemService.delete_for_category(
            restaurant_uuid,
            _parse_uuid(menu_id, "menuId"),
            _parse_uuid(category_id, "categoryId"),
            _parse_uuid(item_id, "itemId"),
        )

    @staticmethod
    def list_tables(*, restaurant_id: str | UUID, **auth) -> dict:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        return TableService.get_all(restaurant_uuid)

    @staticmethod
    def create_table(*, restaurant_id: str | UUID, body: dict, **auth) -> dict:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        if "groups" in body:
            return TableService.create_bulk(restaurant_uuid, body.get("groups"))
        return TableService.create(
            restaurant_uuid,
            body.get("number"),
            body.get("capacity"),
            name=body.get("name"),
            is_joinable=body.get("isJoinable", True),
        )

    @staticmethod
    def get_table(*, restaurant_id: str | UUID, table_id: str | UUID, **auth) -> dict:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        return TableService.get_by_id(restaurant_uuid, _parse_uuid(table_id, "tableId"))

    @staticmethod
    def update_table(
        *,
        restaurant_id: str | UUID,
        table_id: str | UUID,
        body: dict,
        **auth,
    ) -> dict:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        return TableService.update(
            restaurant_uuid,
            _parse_uuid(table_id, "tableId"),
            body.get("number"),
            body.get("capacity"),
            name=body.get("name"),
            is_joinable=body.get("isJoinable", True),
            is_active=body.get("isActive", True),
        )

    @staticmethod
    def delete_table(*, restaurant_id: str | UUID, table_id: str | UUID, **auth) -> None:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        TableService.delete(restaurant_uuid, _parse_uuid(table_id, "tableId"))

    @staticmethod
    def get_business_hours(*, restaurant_id: str | UUID, **auth) -> dict:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        return BusinessHoursService.get_all(restaurant_uuid)

    @staticmethod
    def update_business_hours(*, restaurant_id: str | UUID, body: dict, **auth) -> dict:
        restaurant_uuid = CognitoRestaurantService._require_admin(restaurant_id, **auth)
        return BusinessHoursService.bulk_update(
            restaurant_uuid,
            body.get("hours", []),
        )

    @staticmethod
    def get_availability(
        *,
        restaurant_id: str | UUID,
        on_date,
        party_size,
    ) -> dict:
        restaurant_uuid = _parse_uuid(restaurant_id, "restaurantId")
        parsed_date = ReservationServiceShim.parse_required_date(on_date)
        try:
            parsed_party_size = int(party_size)
        except (TypeError, ValueError) as error:
            raise ValidationError(
                "partySize must be a positive integer.",
                {"partySize": "Invalid integer"},
            ) from error
        return AvailabilityService.get_availability_payload(
            restaurant_uuid,
            parsed_date,
            parsed_party_size,
        )

    @staticmethod
    def _require_admin(
        restaurant_id: str | UUID,
        *,
        cognito_sub: str | None,
        is_cognito_admin: bool = False,
    ) -> UUID:
        restaurant_uuid = _parse_uuid(restaurant_id, "restaurantId")
        principal = CognitoAuthorizationService.principal_user(cognito_sub)
        CognitoAuthorizationService.require_restaurant_admin(
            principal=principal,
            restaurant_id=restaurant_uuid,
            is_cognito_admin=is_cognito_admin,
        )
        return restaurant_uuid

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


class ReservationServiceShim:
    @staticmethod
    def parse_required_date(value):
        from app.services.reservation_service import ReservationService

        return ReservationService.parse_required_date(value)


def _strip_cognito_sub(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "cognitoSub"}
