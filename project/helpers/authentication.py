import logging
from functools import wraps

from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt.exceptions import PyJWTError

logger = logging.getLogger(__name__)


def require_authentication():
    """
    Decorator factory that protects a route with JWT authentication.

    Expects the request to include a valid JWT in the Authorization header
    using the Bearer scheme: ``Authorization: Bearer <token>``.

    Returns 401 if the token is missing, expired, or invalid.

    Usage::

        @namespace.route("/protected")
        class MyResource(Resource):
            @require_authentication()
            def get(self):
                ...
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except (JWTExtendedException, PyJWTError) as e:
                logger.warning(f"JWT authentication failed: {e}")
                return jsonify(
                    {"error": "Missing or invalid authentication token."}
                ), 401
            return f(*args, **kwargs)

        return wrapper

    return decorator
