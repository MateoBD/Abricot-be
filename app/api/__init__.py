from flask import Blueprint, Flask
from flask_restx import Api
from flask_restx.resource import Resource
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from app.exceptions.errors import AppError
from app.error_handlers import (
    app_error_payload,
    http_exception_payload,
    integrity_error_payload,
    log_handled_error,
    unexpected_error_payload,
    value_error_payload,
)

def register_blueprints(app: Flask) -> None:
    from app.api.auth.routes import (
        access_tokens_namespace,
        namespace as sessions_namespace,
    )
    from app.api.reservations.routes import namespace as reservations_namespace
    from app.api.restaurants.routes import namespace as restaurant_namespace
    from app.api.system.lookup_routes import namespace as lookup_namespace
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
    api.add_namespace(sessions_namespace)
    api.add_namespace(access_tokens_namespace)
    api.add_namespace(system_namespace)
    api.add_namespace(lookup_namespace)
    api.add_namespace(users_namespace)
    api.add_namespace(restaurant_namespace)
    api.add_namespace(reservations_namespace)
    app.register_blueprint(blueprint)

    def _compat_validate_payload(self, expect, collection=False):
        from flask import request

        data = request.get_json()
        resolver = getattr(self.api, "refresolver", None)
        if resolver is None:
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
    def handle_app_error(error: AppError):
        payload, status_code = app_error_payload(error)
        log_handled_error(error, payload, status_code)
        return payload, status_code

    @api.errorhandler(IntegrityError)
    def handle_integrity_error(error: IntegrityError):
        payload, status_code = integrity_error_payload(error)
        log_handled_error(error, payload, status_code)
        return payload, status_code

    @api.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        payload, status_code = http_exception_payload(error)
        log_handled_error(error, payload, status_code)
        return payload, status_code

    @api.errorhandler(ValueError)
    def handle_value_error(error: ValueError):
        payload, status_code = value_error_payload(error)
        log_handled_error(error, payload, status_code)
        return payload, status_code

    @api.errorhandler(Exception)
    def handle_unexpected(error: Exception):
        payload, status_code = unexpected_error_payload(error)
        log_handled_error(error, payload, status_code)
        return payload, status_code
