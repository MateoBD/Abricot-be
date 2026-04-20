from enum import Enum


class UserRole(str, Enum):
    """Rol de usuario (Abricot proposal §4)."""

    CUSTOMER = "CUSTOMER"
    RESTAURANT_ADMIN = "RESTAURANT_ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"
