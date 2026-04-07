"""Import all ORM models so Flask-Migrate can detect them during migrations."""

from project.models.restaurant_model import RestaurantModel
from project.models.user_model import UserModel

__all__ = ["UserModel", "RestaurantModel"]
