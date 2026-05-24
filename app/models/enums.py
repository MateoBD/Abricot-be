from enum import Enum


class UserRole(str, Enum):
    """Rol de usuario (Abricot proposal §4)."""

    CUSTOMER = "CUSTOMER"
    RESTAURANT_ADMIN = "RESTAURANT_ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class UserSnsSubscriptionStatus(str, Enum):
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


class ReservationSource(str, Enum):
    ONLINE = "ONLINE"
    PHONE = "PHONE"
    EVENT = "EVENT"


class ReservationStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    READY = "READY"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class DiscountType(str, Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED_AMOUNT = "FIXED_AMOUNT"
    FREE_ITEM = "FREE_ITEM"
