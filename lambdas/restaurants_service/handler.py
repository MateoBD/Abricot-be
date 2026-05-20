import json
import logging
from typing import Any, Callable

from app.services.cognito_restaurant_service import CognitoRestaurantService
from common.flask_db import backend_app_context

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _json_response(status_code: int, payload: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(payload, default=str),
    }


def _route_path(event: dict) -> str:
    return (
        event.get("rawPath")
        or event.get("path")
        or event.get("requestContext", {}).get("http", {}).get("path")
        or ""
    )


def _method(event: dict) -> str:
    return (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or ""
    ).upper()


def _json_body(event: dict) -> dict:
    raw_body = event.get("body")
    if not raw_body:
        return {}
    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        return {}
    return body if isinstance(body, dict) else {}


def _authorizer_claims(event: dict) -> dict[str, Any]:
    authorizer = event.get("requestContext", {}).get("authorizer") or {}
    if isinstance(authorizer.get("claims"), dict):
        return authorizer["claims"]
    jwt = authorizer.get("jwt") or {}
    if isinstance(jwt.get("claims"), dict):
        return jwt["claims"]
    return {}


def _claim_sub(claims: dict[str, Any]) -> str | None:
    sub = claims.get("sub")
    return str(sub).strip() if sub else None


def _app_error_response(error) -> dict:
    from app.exceptions.errors import AppError

    if not isinstance(error, AppError):
        raise error
    payload = {"message": error.public_message or error.message}
    if error.payload:
        payload["errors"] = error.payload
    return _json_response(error.status_code, payload)


def _database_error_response(error: RuntimeError) -> dict:
    logger.warning(
        "restaurants_service_db_configuration_error type=%s",
        str(error).split(":", 1)[0],
    )
    return _json_response(
        500, {"message": "Restaurants service database is not configured."}
    )


def _unexpected_error_response(route: str, error: Exception) -> dict:
    logger.warning("%s_failed type=%s", route, type(error).__name__)
    return _json_response(500, {"message": "Restaurants service failed."})


def _with_backend(route: str, operation: Callable[[], tuple[int, dict]]) -> dict:
    from app.exceptions.errors import AppError

    try:
        with backend_app_context():
            status_code, payload = operation()
            return _json_response(status_code, payload)
    except AppError as exc:
        return _app_error_response(exc)
    except RuntimeError as exc:
        if str(exc).startswith(("missing_db_env", "invalid_db_target")):
            return _database_error_response(exc)
        return _unexpected_error_response(route, exc)
    except Exception as exc:
        return _unexpected_error_response(route, exc)


def _handle_post_restaurants(event: dict) -> dict:
    claims = _authorizer_claims(event)

    def operation() -> tuple[int, dict]:
        return 201, CognitoRestaurantService.create_restaurant(
            cognito_sub=_claim_sub(claims),
            body=_json_body(event),
        )

    return _with_backend("restaurants_post", operation)


def handler(event, context):
    event = event or {}
    method = _method(event)
    path = _route_path(event).rstrip("/")

    if method == "POST" and path == "/restaurants":
        return _handle_post_restaurants(event)

    return _json_response(404, {"message": "Route not found."})
