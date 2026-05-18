import logging

from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity

from app.exceptions.errors import ConflictError, UnauthorizedError, ValidationError
from app.extensions import bcrypt
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class AuthService:
    @staticmethod
    def register(
        email: str,
        password: str,
        name: str,
        surname: str,
        role: str | None = None,
    ) -> dict:
        email = email.strip().lower()
        name = name.strip()
        surname = surname.strip()

        if len(password) < 8:
            raise ValidationError(
                "Password must be at least 8 characters.",
                {"password": "Too short"},
            )

        if UserRepository.get_by_email(email):
            raise ConflictError(
                "An account with this email already exists.",
                {"email": "Already in use"},
            )

        raw_role = (role or "").strip().upper() or UserRole.CUSTOMER.value
        try:
            user_role = UserRole(raw_role)
        except ValueError as error:
            raise ValidationError(
                "Invalid role.",
                {"role": "Must be CUSTOMER or RESTAURANT_ADMIN"},
            ) from error
        if user_role not in (UserRole.CUSTOMER, UserRole.RESTAURANT_ADMIN):
            raise ValidationError(
                "This role cannot be set via public registration.",
                {"role": "Not allowed for self-service registration"},
            )

        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        user = UserRepository.create(
            email=email,
            password_hash=password_hash,
            name=name,
            surname=surname,
            role=user_role,
        )
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        logger.info(f"New user registered: id={user.id}")
        return {
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "user": user.to_dict(),
        }

    @staticmethod
    def login(email: str, password: str) -> dict:
        email = email.strip().lower()
        user = UserRepository.get_by_email(email)

        if (
            not user
            or user.password_hash.startswith("COGNITO_ONLY:")
            or not bcrypt.check_password_hash(user.password_hash, password)
        ):
            raise UnauthorizedError(
                "Invalid email or password.",
                public_message="Invalid email or password.",
            )

        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        logger.info(f"User logged in: id={user.id}")
        return {
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "user": user.to_dict(),
        }

    @staticmethod
    def refresh() -> dict:
        """
        Issues a new access token using the refresh token already verified by
        require_refresh_token(). Call get_jwt_identity() here — it is valid
        because verify_jwt_in_request(refresh=True) has already run.
        """
        user_id = get_jwt_identity()
        new_access_token = create_access_token(identity=user_id)
        logger.info(f"Access token refreshed for user_id={user_id}")
        return {"accessToken": new_access_token}
