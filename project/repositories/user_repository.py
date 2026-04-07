from project import db
from project.models.user_model import UserModel


class UserRepository:
    """Handles all database operations related to UserModel."""

    @classmethod
    def create(
        cls, email: str, password_hash: str, name: str, surname: str
    ) -> UserModel:
        """
        Inserts a new user into the database.

        Args:
            email: The user's email address.
            password_hash: Bcrypt hash of the user's password.
            name: The user's first name.
            surname: The user's last name.

        Returns:
            The newly created UserModel instance.

        Raises:
            sqlalchemy.exc.IntegrityError: If a user with the same email already exists.
        """
        user = UserModel(
            email=email, password_hash=password_hash, name=name, surname=surname
        )
        db.session.add(user)
        db.session.commit()
        return user

    @classmethod
    def get_by_email(cls, email: str) -> UserModel | None:
        """
        Retrieves a user by their email address.

        Args:
            email: The email address to look up.

        Returns:
            The matching UserModel instance, or None if not found.
        """
        return UserModel.query.filter_by(email=email).first()

    @classmethod
    def get_by_id(cls, user_id: int) -> UserModel | None:
        """
        Retrieves a user by their primary key.

        Args:
            user_id: The user's ID.

        Returns:
            The matching UserModel instance, or None if not found.
        """
        return UserModel.query.get(user_id)
