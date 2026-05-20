from uuid import UUID

from app.exceptions.errors import ForbiddenError, UnauthorizedError, ValidationError
from app.models.enums import UserRole
from app.models.user import UserModel
from app.repositories.restaurant_admin_repository import RestaurantAdminRepository
from app.repositories.user_repository import UserRepository

_PRIVILEGE_BODY_KEYS = frozenset(
    {
        "role",
        "isAdmin",
        "creatorUserId",
        "adminUserId",
        "cognitoSub",
        "cognito_sub",
    }
)


class CognitoAuthorizationService:
    @staticmethod
    def reject_privilege_fields(data: dict, *, allow_user_id: bool = False) -> None:
        blocked = set(_PRIVILEGE_BODY_KEYS)
        if not allow_user_id:
            blocked.add("userId")
        rejected = sorted(key for key in data if key in blocked)
        if rejected:
            raise ValidationError(
                "Privilege fields are not allowed in this request.",
                {key: "Not allowed" for key in rejected},
            )

    @staticmethod
    def principal_user(cognito_sub: str | None) -> UserModel:
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
    def is_super_admin(principal: UserModel, *, is_cognito_admin: bool = False) -> bool:
        return principal.role == UserRole.SUPER_ADMIN or is_cognito_admin

    @staticmethod
    def require_same_user_or_super_admin(
        *,
        principal: UserModel,
        target_user_id: UUID,
        is_cognito_admin: bool = False,
    ) -> None:
        if principal.id == target_user_id:
            return
        if CognitoAuthorizationService.is_super_admin(
            principal,
            is_cognito_admin=is_cognito_admin,
        ):
            return
        raise ForbiddenError("Forbidden.", public_message="Forbidden.")

    @staticmethod
    def require_restaurant_admin(
        *,
        principal: UserModel,
        restaurant_id: UUID,
        is_cognito_admin: bool = False,
    ) -> None:
        if CognitoAuthorizationService.is_super_admin(
            principal,
            is_cognito_admin=is_cognito_admin,
        ):
            return
        if principal.role != UserRole.RESTAURANT_ADMIN:
            raise ForbiddenError("Forbidden.", public_message="Forbidden.")
        if not RestaurantAdminRepository.is_admin(
            user_id=principal.id,
            restaurant_id=restaurant_id,
        ):
            raise ForbiddenError("Forbidden.", public_message="Forbidden.")


def public_user_payload(user: UserModel) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "surname": user.surname,
        "role": user.role.value,
        "createdAt": user.created_at.isoformat(),
    }
