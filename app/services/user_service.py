import logging
from uuid import UUID

from app.exceptions.errors import NotFoundError, UnauthorizedError, ValidationError
from app.extensions import bcrypt
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserService:
    @staticmethod
    def get_profile(user_id: UUID) -> dict:
        user = UserRepository.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with id={user_id} not found.")
        return user.to_dict()

    @staticmethod
    def update_profile(user_id: UUID, name: str, surname: str) -> dict:
        user = UserRepository.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with id={user_id} not found.")

        name = name.strip()
        surname = surname.strip()

        if not name:
            raise ValidationError("Name is required.", {"name": "Cannot be empty"})
        if not surname:
            raise ValidationError("Surname is required.", {"surname": "Cannot be empty"})

        user = UserRepository.update_profile(user, name=name, surname=surname)
        logger.info("User profile updated: id=%s", user.id)
        return user.to_dict()

    @staticmethod
    def change_password(user_id: UUID, current_password: str, new_password: str) -> None:
        user = UserRepository.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with id={user_id} not found.")

        if not bcrypt.check_password_hash(user.password_hash, current_password):
            raise UnauthorizedError(
                "Current password is incorrect.",
                {"currentPassword": "Invalid password"},
            )

        if len(new_password) < 8:
            raise ValidationError(
                "New password must be at least 8 characters.",
                {"newPassword": "Too short"},
            )

        new_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
        UserRepository.update_password_hash(user, password_hash=new_hash)
        logger.info("User password changed: id=%s", user.id)
