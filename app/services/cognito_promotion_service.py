from uuid import UUID

from app.exceptions.errors import ValidationError
from app.services.cognito_authorization_service import CognitoAuthorizationService
from app.services.promotion_service import PromotionService


def _parse_uuid(value: str | UUID | None, field: str) -> UUID:
    if value is None or value == "":
        raise ValidationError(f"{field} is required.", {field: "Required"})
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError as error:
        raise ValidationError("Invalid identifier format.", {field: "Invalid UUID"}) from error


class CognitoPromotionService:
    @staticmethod
    def list_for_restaurant(
        *,
        restaurant_id: str | UUID,
        cognito_sub: str | None,
        is_cognito_admin: bool = False,
    ) -> dict:
        restaurant_uuid = CognitoPromotionService._require_admin(
            restaurant_id,
            cognito_sub=cognito_sub,
            is_cognito_admin=is_cognito_admin,
        )
        return PromotionService.get_all_for_admin(restaurant_uuid)

    @staticmethod
    def get_by_id(
        *,
        restaurant_id: str | UUID,
        promotion_id: str | UUID,
        cognito_sub: str | None,
        is_cognito_admin: bool = False,
    ) -> dict:
        restaurant_uuid = CognitoPromotionService._require_admin(
            restaurant_id,
            cognito_sub=cognito_sub,
            is_cognito_admin=is_cognito_admin,
        )
        return PromotionService.get_by_id(
            restaurant_uuid,
            _parse_uuid(promotion_id, "promotionId"),
        )

    @staticmethod
    def create(
        *,
        restaurant_id: str | UUID,
        cognito_sub: str | None,
        body: dict,
        is_cognito_admin: bool = False,
    ) -> dict:
        restaurant_uuid = CognitoPromotionService._require_admin(
            restaurant_id,
            cognito_sub=cognito_sub,
            is_cognito_admin=is_cognito_admin,
        )
        return PromotionService.create(
            restaurant_id=restaurant_uuid,
            title=body.get("title", ""),
            description=body.get("description"),
            discount_type=str(body.get("discountType", "")),
            discount_value=body.get("discountValue"),
            start_date=str(body.get("startDate", "")),
            end_date=str(body.get("endDate", "")),
            notify_users=bool(body.get("notifyUsers", False)),
            menu_item_ids=body.get("menuItemIds"),
        )

    @staticmethod
    def delete(
        *,
        restaurant_id: str | UUID,
        promotion_id: str | UUID,
        cognito_sub: str | None,
        is_cognito_admin: bool = False,
    ) -> None:
        restaurant_uuid = CognitoPromotionService._require_admin(
            restaurant_id,
            cognito_sub=cognito_sub,
            is_cognito_admin=is_cognito_admin,
        )
        PromotionService.delete(
            restaurant_uuid,
            _parse_uuid(promotion_id, "promotionId"),
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
