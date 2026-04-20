"""Import all ORM models so Flask-Migrate can detect them during migrations."""

from app.models.enums import UserRole  # noqa: F401
from app.models.restaurant import RestaurantModel  # noqa: F401
from app.models.user import UserModel  # noqa: F401

__all__ = ["RestaurantModel", "UserModel", "UserRole"]
