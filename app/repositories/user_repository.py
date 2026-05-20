from uuid import UUID

from sqlalchemy import func

from app.extensions import db
from app.models.enums import UserRole
from app.models.user import UserModel


class UserRepository:
    @staticmethod
    def create(
        email: str,
        password_hash: str,
        name: str,
        surname: str,
        *,
        role: UserRole = UserRole.CUSTOMER,
        cognito_sub: str | None = None,
    ) -> UserModel:
        user = UserModel(
            email=email,
            password_hash=password_hash,
            name=name,
            surname=surname,
            role=role,
            cognito_sub=cognito_sub,
        )
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def get_by_email(email: str) -> UserModel | None:
        return db.session.execute(
            db.select(UserModel).where(UserModel.email == email)
        ).scalar_one_or_none()

    @staticmethod
    def get_by_email_case_insensitive(email: str) -> UserModel | None:
        return db.session.execute(
            db.select(UserModel).where(func.lower(UserModel.email) == email.lower())
        ).scalar_one_or_none()

    @staticmethod
    def get_by_cognito_sub(cognito_sub: str) -> UserModel | None:
        return db.session.execute(
            db.select(UserModel).where(UserModel.cognito_sub == cognito_sub)
        ).scalar_one_or_none()

    @staticmethod
    def get_by_id(user_id: UUID) -> UserModel | None:
        return db.session.get(UserModel, user_id)

    @staticmethod
    def update_role(
        user_id: UUID,
        role: UserRole,
        *,
        auto_commit: bool = True,
    ) -> UserModel | None:
        user = UserRepository.get_by_id(user_id)
        if not user:
            return None
        user.role = role
        if auto_commit:
            db.session.commit()
        return user

    @staticmethod
    def update_profile(user: UserModel, *, name: str, surname: str) -> UserModel:
        user.name = name
        user.surname = surname
        db.session.commit()
        return user

    @staticmethod
    def link_cognito_sub(user: UserModel, *, cognito_sub: str) -> UserModel:
        user.cognito_sub = cognito_sub
        db.session.commit()
        return user

    @staticmethod
    def update_password_hash(user: UserModel, *, password_hash: str) -> UserModel:
        user.password_hash = password_hash
        db.session.commit()
        return user
