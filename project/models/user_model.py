from datetime import datetime, timezone

from project import db


class UserModel(db.Model):
    """
    Represents a registered user in the system.

    Attributes:
        id (int): Auto-incremented primary key.
        email (str): Unique email address used for login.
        password_hash (str): Bcrypt hash of the user's password.
        name (str): First name of the user.
        surname (str): Last name of the user.
        created_at (datetime): UTC timestamp of when the user was created.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        """Serializes the user instance to a dictionary (excludes password_hash)."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "surname": self.surname,
            "createdAt": self.created_at.isoformat(),
        }
