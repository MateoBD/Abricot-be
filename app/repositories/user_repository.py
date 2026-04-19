from app.extensions import db
from app.models.user import UserModel


class UserRepository:
    @staticmethod
    def create(email: str, password_hash: str, name: str, surname: str) -> UserModel:
        user = UserModel(
            email=email, password_hash=password_hash, name=name, surname=surname
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
    def get_by_id(user_id: int) -> UserModel | None:
        return db.session.get(UserModel, user_id)
