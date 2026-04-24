import logging

from flask import Blueprint, Flask
from flask_restx import Api
from flask_restx.resource import Resource
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from app.exceptions.errors import AppError

logger = logging.getLogger(__name__)


def register_blueprints(app: Flask) -> None:
    from app.api.auth.routes import namespace as auth_namespace
    from app.api.restaurants.routes import namespace as restaurant_namespace
    from app.api.system.routes import namespace as system_namespace
    from app.api.users.routes import namespace as users_namespace

    blueprint = Blueprint("api", __name__, url_prefix="/")

    api = Api(
        blueprint,
        title="Abricot Backend API",
        version="1.0",
        description="Documentation of the Abricot Backend API",
        authorizations={
            "Bearer": {
                "type": "apiKey",
                "in": "header",
                "name": "Authorization",
                "description": "Enter: Bearer <JWT token>",
            }
        },
        security="Bearer",
    )

    _register_api_error_handlers(api)
    api.add_namespace(auth_namespace)
    api.add_namespace(system_namespace)
    api.add_namespace(users_namespace)
    api.add_namespace(restaurant_namespace)
    app.register_blueprint(blueprint)

    def _compat_validate_payload(self, expect, collection=False):
        from flask import request

        data = request.get_json()
        resolver = getattr(self.api, "_refresolver", None)
        format_checker = getattr(self.api, "format_checker", None)
        if collection:
            data = data if isinstance(data, list) else [data]
            for obj in data:
                expect.validate(obj, resolver, format_checker)
        else:
            expect.validate(data, resolver, format_checker)

    Resource._Resource__validate_payload = _compat_validate_payload


def _register_api_error_handlers(api: Api) -> None:
    @api.errorhandler(AppError)
    def handle_app_error(e: AppError):
        return {
            "message": e.message,
            "code": e.code,
            "errors": e.payload,
        }, e.status_code

    @api.errorhandler(IntegrityError)
    def handle_integrity_error(e: IntegrityError):
        logger.warning(f"IntegrityError: {e}")
        return {
            "message": "Resource already exists.",
            "code": "CONFLICT",
            "errors": {},
        }, 409

    @api.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        return {
            "message": e.description,
            "code": type(e).__name__,
            "errors": {},
        }, e.code

    @api.errorhandler(ValueError)
    def handle_value_error(e: ValueError):
        return {"message": str(e), "code": "VALUE_ERROR", "errors": {}}, 400

    @api.errorhandler(Exception)
    def handle_unexpected(e: Exception):
        logger.exception("Unexpected error in API layer")
        return {
            "message": "Internal server error.",
            "code": "INTERNAL_ERROR",
            "errors": {},
        }, 500
