from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from app.exceptions.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.models.enums import UserRole
from app.models.user import UserModel
from app.repositories.user_repository import UserRepository
from app.services.sns_user_notification_service import SnsUserNotificationService
from app.services.user_service import UserService

_PRIVILEGE_BODY_KEYS = frozenset(
    {"role", "isAdmin", "userId", "adminUserId", "creatorUserId"}
)


class AccountType(str, Enum):
    CUSTOMER = "customer"
    RESTAURANT_OWNER = "restaurant_owner"


@dataclass(frozen=True)
class CognitoProvisionResult:
    user: dict
    created: bool


def _parse_uuid(value: str | UUID | None, field: str) -> UUID:
    if value is None or value == "":
        raise ValidationError(f"{field} is required.", {field: "Required"})
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError as error:
        raise ValidationError("Invalid identifier format.", {field: "Invalid UUID"}) from error


def _user_payload(user: UserModel) -> dict:
    return user.to_dict()


def _default_name(email: str, given_name: str | None) -> str:
    name = (given_name or "").strip()
    return name or email.split("@", 1)[0] or "Cognito"


def _default_surname(family_name: str | None) -> str:
    return (family_name or "").strip() or "User"


class CognitoUserService:
    @staticmethod
    def reject_privilege_fields(data: dict) -> None:
        rejected = sorted(key for key in data if key in _PRIVILEGE_BODY_KEYS)
        if rejected:
            raise ValidationError(
                "Privilege fields are not allowed in this request.",
                {key: "Not allowed" for key in rejected},
            )

    @staticmethod
    def parse_account_type(data: dict, *, required: bool) -> AccountType | None:
        raw = data.get("accountType")
        if raw is None:
            raw = data.get("onboardingType")
        if raw is None or raw == "":
            if required:
                raise ValidationError(
                    "accountType is required for new users.",
                    {"accountType": "Required"},
                )
            return None
        if not isinstance(raw, str):
            raise ValidationError("Invalid accountType.", {"accountType": "Invalid"})
        normalized = raw.strip().lower()
        try:
            return AccountType(normalized)
        except ValueError as error:
            raise ValidationError(
                "accountType must be customer or restaurant_owner.",
                {"accountType": "Invalid"},
            ) from error

    @staticmethod
    def provision_user(
        *,
        cognito_sub: str | None,
        email: str | None,
        given_name: str | None = None,
        family_name: str | None = None,
        account_type: AccountType | None = None,
    ) -> CognitoProvisionResult:
        cognito_sub = (cognito_sub or "").strip()
        if not cognito_sub:
            raise UnauthorizedError(
                "Missing Cognito sub claim.",
                public_message="Missing Cognito sub claim.",
            )

        existing = UserRepository.get_by_cognito_sub(cognito_sub)
        if existing:
            refreshed = UserRepository.get_by_id(existing.id) or existing
            return CognitoProvisionResult(_user_payload(refreshed), created=False)

        email = (email or "").strip().lower()
        if not email:
            raise ValidationError(
                (
                    "Email claim is required for first Cognito provisioning. "
                    "Use the ID token for POST /users."
                ),
                {"email": "Required"},
            )

        if account_type is None:
            raise ValidationError(
                "accountType is required for new users.",
                {"accountType": "Required"},
            )

        user = UserRepository.get_by_email_case_insensitive(email)
        if user:
            linked_sub = user.cognito_sub
            if linked_sub and linked_sub != cognito_sub:
                raise ConflictError("Email is already linked to another Cognito user.")
            linked = UserRepository.link_cognito_sub(user, cognito_sub=cognito_sub)
            refreshed = UserRepository.get_by_id(linked.id) or linked
            return CognitoProvisionResult(_user_payload(refreshed), created=False)

        created = UserRepository.create(
            email=email,
            password_hash=f"COGNITO_ONLY:{cognito_sub}",
            name=_default_name(email, given_name),
            surname=_default_surname(family_name),
            role=UserRole.CUSTOMER,
            cognito_sub=cognito_sub,
        )
        payload = _user_payload(created)
        if account_type == AccountType.RESTAURANT_OWNER:
            payload = {**payload, "nextStep": "restaurant_onboarding"}
        return CognitoProvisionResult(payload, created=True)

    @staticmethod
    def list_restaurants_for_principal(
        *,
        user_id: str | UUID,
        cognito_sub: str | None,
        is_cognito_admin: bool = False,
    ) -> dict:
        target_id = _parse_uuid(user_id, "userId")
        principal = CognitoUserService._principal_user(cognito_sub)
        CognitoUserService._require_same_user_or_admin(
            principal=principal,
            target_id=target_id,
            is_cognito_admin=is_cognito_admin,
        )
        return UserService.get_my_restaurants(target_id)

    @staticmethod
    def get_profile_for_principal(
        *,
        user_id: str | UUID,
        cognito_sub: str | None,
        is_cognito_admin: bool = False,
    ) -> dict:
        target_id = _parse_uuid(user_id, "userId")
        principal = CognitoUserService._principal_user(cognito_sub)
        CognitoUserService._require_same_user_or_admin(
            principal=principal,
            target_id=target_id,
            is_cognito_admin=is_cognito_admin,
        )

        user = UserRepository.get_by_id(target_id)
        if not user:
            raise NotFoundError("User not found.", public_message="User not found.")
        user = SnsUserNotificationService.refresh_subscription_status(user)
        return _user_payload(user)

    @staticmethod
    def update_profile_for_principal(
        *,
        user_id: str | UUID,
        cognito_sub: str | None,
        data: dict,
        is_cognito_admin: bool = False,
    ) -> dict:
        target_id = _parse_uuid(user_id, "userId")
        principal = CognitoUserService._principal_user(cognito_sub)
        CognitoUserService._require_same_user_or_admin(
            principal=principal,
            target_id=target_id,
            is_cognito_admin=is_cognito_admin,
        )

        user = UserRepository.get_by_id(target_id)
        if not user:
            raise NotFoundError("User not found.", public_message="User not found.")

        name = CognitoUserService._profile_field(data, "name", user.name)
        surname = CognitoUserService._profile_field(data, "surname", user.surname)
        if name == user.name and surname == user.surname:
            return _user_payload(user)

        updated = UserRepository.update_profile(user, name=name, surname=surname)
        return _user_payload(updated)

    @staticmethod
    def _principal_user(cognito_sub: str | None) -> UserModel | None:
        cognito_sub = (cognito_sub or "").strip()
        if not cognito_sub:
            return None
        return UserRepository.get_by_cognito_sub(cognito_sub)

    @staticmethod
    def _require_same_user_or_admin(
        *,
        principal: UserModel | None,
        target_id: UUID,
        is_cognito_admin: bool,
    ) -> None:
        if not principal:
            raise ForbiddenError("Forbidden.", public_message="Forbidden.")

        if (
            principal.id == target_id
            or principal.role == UserRole.SUPER_ADMIN
            or is_cognito_admin
        ):
            return

        raise ForbiddenError("Forbidden.", public_message="Forbidden.")

    @staticmethod
    def _profile_field(data: dict, name: str, current_value: str) -> str:
        if name not in data or data.get(name) is None:
            return current_value

        value = data.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"Invalid {name}.", {name: "Cannot be empty"})
        return value.strip()
