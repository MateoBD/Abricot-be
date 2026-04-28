"""Import all ORM models so Flask-Migrate can detect them during migrations."""

from app.models.business_hours import BusinessHoursModel  # noqa: F401
from app.models.cuisine_type import CuisineTypeModel  # noqa: F401
from app.models.enums import (  # noqa: F401
	DiscountType,
	OrderStatus,
	ReservationSource,
	ReservationStatus,
	UserRole,
)
from app.models.location import CityModel, CountryModel, NeighbourhoodModel, ProvinceModel  # noqa: F401
from app.models.menu import MenuModel  # noqa: F401
from app.models.menu_category import MenuCategoryModel  # noqa: F401
from app.models.menu_item import MenuItemModel  # noqa: F401
from app.models.notification_event import NotificationEventModel  # noqa: F401
from app.models.notification_preference import NotificationPreferenceModel  # noqa: F401
from app.models.order import OrderModel  # noqa: F401
from app.models.order_item import OrderItemModel  # noqa: F401
from app.models.price_range import PriceRangeModel  # noqa: F401
from app.models.promotion import PromotionModel  # noqa: F401
from app.models.promotion_item import PromotionItemModel  # noqa: F401
from app.models.reservation import ReservationModel  # noqa: F401
from app.models.reservation_table import ReservationTableModel  # noqa: F401
from app.models.restaurant_admin import RestaurantAdminModel  # noqa: F401
from app.models.restaurant_cuisine import RestaurantCuisineModel  # noqa: F401
from app.models.restaurant import RestaurantModel  # noqa: F401
from app.models.restaurant_review import RestaurantReviewModel  # noqa: F401
from app.models.table import TableModel  # noqa: F401
from app.models.user import UserModel  # noqa: F401

__all__ = [
	"BusinessHoursModel",
	"CityModel",
	"CountryModel",
	"CuisineTypeModel",
	"DiscountType",
	"MenuCategoryModel",
	"MenuItemModel",
	"MenuModel",
	"NeighbourhoodModel",
	"NotificationEventModel",
	"NotificationPreferenceModel",
	"OrderItemModel",
	"OrderModel",
	"OrderStatus",
	"PriceRangeModel",
	"PromotionItemModel",
	"PromotionModel",
	"ProvinceModel",
	"ReservationModel",
	"ReservationSource",
	"ReservationStatus",
	"ReservationTableModel",
	"RestaurantAdminModel",
	"RestaurantCuisineModel",
	"RestaurantModel",
	"RestaurantReviewModel",
	"TableModel",
	"UserModel",
	"UserRole",
]
