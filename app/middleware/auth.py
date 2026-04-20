import logging
from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt.exceptions import PyJWTError

from app.models.enums import UserRole
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
                return jsonify(_UNAUTHORIZED_RESPONSE), 401
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
                return jsonify(_UNAUTHORIZED_RESPONSE), 401
            return f(*args, **kwargs)

        return wrapper

    return decorator


def get_current_user_id() -> int:
    """Returns the authenticated user's ID. Only valid inside a protected route."""
    return int(get_jwt_identity())


def require_roles(*allowed_roles: UserRole):
    """Allows only users with one of the provided roles (or SUPER_ADMIN when included)."""

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except (JWTExtendedException, PyJWTError) as e:
                logger.warning(f"Access token validation failed: {e}")
                return jsonify(_UNAUTHORIZED_RESPONSE), 401

            user_id = get_current_user_id()
            user = UserRepository.get_by_id(user_id)
            if not user:
                logger.warning(f"Authenticated user does not exist: user_id={user_id}")
                return jsonify(_UNAUTHORIZED_RESPONSE), 401

            if user.role not in allowed_roles:
                logger.warning(
                    "Role check failed for user_id=%s required=%s actual=%s",
                    user_id,
                    [role.value for role in allowed_roles],
                    user.role.value,
                )
                return jsonify(_FORBIDDEN_RESPONSE), 403

            return f(*args, **kwargs)

        return wrapper

    return decorator


def require_restaurant_admin(restaurant_id_param: str):
    """
    Validates that the caller is a restaurant admin (or super admin).

    Until `restaurant_admins` is introduced, this base guard validates by role.
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            restaurant_id = kwargs.get(restaurant_id_param)
            if restaurant_id is None:
                logger.warning(
                    "Missing restaurant id path param '%s' in protected route.",
                    restaurant_id_param,
                )
                return jsonify(_FORBIDDEN_RESPONSE), 403

            return require_roles(UserRole.RESTAURANT_ADMIN, UserRole.SUPER_ADMIN)(f)(
                *args, **kwargs
            )

        return wrapper

    return decorator
