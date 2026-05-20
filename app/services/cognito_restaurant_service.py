from app.exceptions.errors import UnauthorizedError, ValidationError
from app.models.user import UserModel
from app.repositories.user_repository import UserRepository
from app.services.restaurant_service import RestaurantService

_PRIVILEGE_BODY_KEYS = frozenset(
    {"userId", "role", "creatorUserId", "adminUserId", "isAdmin"}
)


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
