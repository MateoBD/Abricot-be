import logging
from functools import wraps
from uuid import UUID

from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt.exceptions import PyJWTError

from app.exceptions.errors import ForbiddenError, UnauthorizedError
from app.models.enums import UserRole
from app.repositories.restaurant_admin_repository import RestaurantAdminRepository
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

_UNAUTHORIZED_RESPONSE = {
    "message": "Missing or invalid authentication token.",
    "code": "UNAUTHORIZED",
    "errors": {},
}

_FORBIDDEN_RESPONSE = {
    "message": "You do not have permission to access this resource.",
    "code": "FORBIDDEN",
    "errors": {},
}


def require_authentication():
    """
    Protects an endpoint with a JWT access token.

    The client must send:
        Authorization: Bearer <access_token>

    Returns 401 if the token is absent, expired, or invalid.
    Use as a method decorator OR as a Namespace-level decorator:
        decorators=[require_authentication()]
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except (JWTExtendedException, PyJWTError) as e:
                logger.warning(f"Access token validation failed: {e}")
                return _UNAUTHORIZED_RESPONSE, 401
            return f(*args, **kwargs)

        return wrapper

    return decorator


def require_refresh_token():
    """
    Protects the token-refresh endpoint. Accepts ONLY refresh tokens.

    The client must send:
        Authorization: Bearer <refresh_token>

    Flask-JWT-Extended distinguishes access from refresh tokens via the
    token_type claim inside the JWT payload. Sending an access token here
    returns 401, and vice-versa — the two token types are not interchangeable.

    Returns 401 if the refresh token is absent, expired, or invalid.
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request(refresh=True)
            except (JWTExtendedException, PyJWTError) as e:
                logger.warning(f"Refresh token validation failed: {e}")
                return _UNAUTHORIZED_RESPONSE, 401
            return f(*args, **kwargs)

        return wrapper

    return decorator


def get_current_user_id() -> UUID:
    """Returns the authenticated user's ID. Only valid inside a protected route."""
    return UUID(get_jwt_identity())


def require_roles(*allowed_roles: UserRole):
    """Allows only users with one of the provided roles (or SUPER_ADMIN when included)."""

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except (JWTExtendedException, PyJWTError) as e:
                logger.warning(f"Access token validation failed: {e}")
                return _UNAUTHORIZED_RESPONSE, 401

            user_id = get_current_user_id()
            user = UserRepository.get_by_id(user_id)
            if not user:
                logger.warning(f"Authenticated user does not exist: user_id={user_id}")
                return _UNAUTHORIZED_RESPONSE, 401

            if user.role not in allowed_roles:
                logger.warning(
                    "Role check failed for user_id=%s required=%s actual=%s",
                    user_id,
                    [role.value for role in allowed_roles],
                    user.role.value,
                )
                return _FORBIDDEN_RESPONSE, 403

            return f(*args, **kwargs)

        return wrapper

    return decorator


def require_restaurant_admin(restaurant_id_param: str):
    """
    Validates that the caller is a restaurant admin for the target restaurant.

    SUPER_ADMIN bypasses ownership checks.
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except (JWTExtendedException, PyJWTError) as e:
                logger.warning(f"Access token validation failed: {e}")
                return _UNAUTHORIZED_RESPONSE, 401

            user_id = get_current_user_id()
            user = UserRepository.get_by_id(user_id)
            if not user:
                logger.warning(f"Authenticated user does not exist: user_id={user_id}")
                return _UNAUTHORIZED_RESPONSE, 401

            restaurant_id = kwargs.get(restaurant_id_param)
            if restaurant_id is None:
                logger.warning(
                    "Missing restaurant id path param '%s' in protected route.",
                    restaurant_id_param,
                )
                return _FORBIDDEN_RESPONSE, 403

            if user.role == UserRole.SUPER_ADMIN:
                return f(*args, **kwargs)

            if user.role != UserRole.RESTAURANT_ADMIN:
                logger.warning(
                    "Restaurant admin check failed for user_id=%s role=%s",
                    user_id,
                    user.role.value,
                )
                return _FORBIDDEN_RESPONSE, 403

            if not RestaurantAdminRepository.is_admin(
                user_id,
                restaurant_id if isinstance(restaurant_id, UUID) else UUID(str(restaurant_id)),
            ):
                logger.warning(
                    "Restaurant ownership check failed for user_id=%s restaurant_id=%s",
                    user_id,
                    restaurant_id,
                )
                return _FORBIDDEN_RESPONSE, 403

            return f(*args, **kwargs)

        return wrapper

    return decorator


def ensure_current_user_is_restaurant_admin(restaurant_id: UUID) -> None:
    """Raises when the current JWT user is not an admin for the restaurant."""
    try:
        verify_jwt_in_request()
    except (JWTExtendedException, PyJWTError) as e:
        logger.warning(f"Access token validation failed: {e}")
        raise UnauthorizedError(
            "Missing or invalid authentication token.",
            {"authorization": "Bearer access token required"},
        ) from e

    user_id = get_current_user_id()
    user = UserRepository.get_by_id(user_id)
    if not user:
        logger.warning(f"Authenticated user does not exist: user_id={user_id}")
        raise UnauthorizedError(
            "Missing or invalid authentication token.",
            {"authorization": "Authenticated user does not exist"},
        )

    if user.role == UserRole.SUPER_ADMIN:
        return

    if user.role != UserRole.RESTAURANT_ADMIN:
        logger.warning(
            "Restaurant admin check failed for user_id=%s role=%s",
            user_id,
            user.role.value,
        )
        raise ForbiddenError(
            "You do not have permission to access this resource.",
            {"authorization": "Restaurant admin role required"},
        )

    if not RestaurantAdminRepository.is_admin(
        user_id=user_id,
        restaurant_id=restaurant_id,
    ):
        logger.warning(
            "Restaurant ownership check failed for user_id=%s restaurant_id=%s",
            user_id,
            restaurant_id,
        )
        raise ForbiddenError(
            "You do not have permission to access this resource.",
            {"authorization": "Restaurant admin assignment required"},
        )


def require_path_user_matches_jwt(user_id_param: str = "user_id"):
    """
    Ensures the URL user id equals the JWT subject (authenticated user).

    Use on ``/users/<user_id>/...`` so a client cannot read or change another
    user's profile. Assumes JWT was already verified (e.g. namespace
    ``require_authentication()``).
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            path_uid = kwargs.get(user_id_param)
            if path_uid is None:
                logger.warning(
                    "Missing path param '%s' for user ownership check.",
                    user_id_param,
                )
                return _FORBIDDEN_RESPONSE, 403

            token_uid = get_current_user_id()
            path_uuid = path_uid if isinstance(path_uid, UUID) else UUID(str(path_uid))
            if path_uuid != token_uid:
                logger.warning(
                    "User id mismatch: path=%s jwt=%s",
                    path_uuid,
                    token_uid,
                )
                return _FORBIDDEN_RESPONSE, 403

            return f(*args, **kwargs)

        return wrapper

    return decorator
