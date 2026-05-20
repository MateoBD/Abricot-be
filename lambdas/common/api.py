import base64
import json
import logging
from typing import Any, Callable
from uuid import UUID

from app.exceptions.errors import AppError, ValidationError
from common.flask_db import backend_app_context


def json_response(status_code: int, payload: dict | None = None) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
    }
    if status_code == 204:
        return {"statusCode": 204, "headers": headers, "body": ""}
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(payload or {}, default=str),
    }


def route_not_found() -> dict:
    return json_response(
        404,
        {"message": "Route not found.", "code": "NOT_FOUND", "errors": {}},
    )


def route_path(event: dict) -> str:
    return (
        event.get("rawPath")
        or event.get("path")
        or event.get("requestContext", {}).get("http", {}).get("path")
        or ""
    )


def method(event: dict) -> str:
    return (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or ""
    ).upper()


def query_params(event: dict) -> dict[str, str]:
    raw = event.get("queryStringParameters") or {}
    return {key: str(value) for key, value in raw.items() if value is not None}


def path_parameters(event: dict) -> dict[str, str]:
    raw = event.get("pathParameters") or {}
    return {key: str(value) for key, value in raw.items() if value is not None}


def json_body(event: dict) -> dict:
    raw_body = event.get("body")
    if not raw_body:
        return {}
    if event.get("isBase64Encoded"):
        try:
            raw_body = base64.b64decode(raw_body).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return {}
    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        return {}
    return body if isinstance(body, dict) else {}


def authorizer_claims(event: dict) -> dict[str, Any]:
    authorizer = event.get("requestContext", {}).get("authorizer") or {}
    if isinstance(authorizer.get("claims"), dict):
        return authorizer["claims"]
    jwt = authorizer.get("jwt") or {}
    if isinstance(jwt.get("claims"), dict):
        return jwt["claims"]
    return {}


def claim_sub(claims: dict[str, Any]) -> str | None:
    sub = claims.get("sub")
    return str(sub).strip() if sub else None


def groups_from_claims(claims: dict[str, Any]) -> list[str]:
    groups = claims.get("cognito:groups") or claims.get("groups")
    if groups is None:
        return []
    if isinstance(groups, list):
        return [str(group) for group in groups]
    if isinstance(groups, str):
        return [group for group in groups.split(",") if group]
    return [str(groups)]


def is_cognito_super_admin(claims: dict[str, Any]) -> bool:
    return "SUPER_ADMIN" in groups_from_claims(claims)


def int_query(query: dict[str, str], name: str, default: int) -> int:
    try:
        return int(query.get(name, str(default)))
    except ValueError:
        return default


def uuid_value(value: str | UUID | None, field: str) -> UUID:
    if value is None or value == "":
        raise ValidationError(f"{field} is required.", {field: "Required"})
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError as error:
        raise ValidationError("Invalid identifier format.", {field: "Invalid UUID"}) from error


def app_error_response(error: AppError) -> dict:
    return json_response(
        error.status_code,
        {
            "message": error.public_message or error.message,
            "code": error.code,
            "errors": error.payload,
        },
    )


def database_error_response(service_name: str, error: RuntimeError, logger: logging.Logger) -> dict:
    logger.warning(
        "%s_db_configuration_error type=%s",
        service_name,
        str(error).split(":", 1)[0],
    )
    return json_response(
        500,
        {
            "message": f"{service_name.replace('_', ' ').title()} database is not configured.",
            "code": "DB_CONFIGURATION_ERROR",
            "errors": {},
        },
    )


def unexpected_error_response(service_name: str, route: str, error: Exception, logger: logging.Logger) -> dict:
    logger.warning("%s_%s_failed type=%s", service_name, route, type(error).__name__)
    return json_response(
        500,
        {
            "message": f"{service_name.replace('_', ' ').title()} failed.",
            "code": "INTERNAL_ERROR",
            "errors": {},
        },
    )


def with_backend(
    service_name: str,
    route: str,
    operation: Callable[[], tuple[int, dict | None]],
    logger: logging.Logger,
) -> dict:
    try:
        with backend_app_context():
            status_code, payload = operation()
            return json_response(status_code, payload)
    except AppError as exc:
        return app_error_response(exc)
    except RuntimeError as exc:
        if str(exc).startswith(("missing_db_env", "invalid_db_target")):
            return database_error_response(service_name, exc, logger)
        return unexpected_error_response(service_name, route, exc, logger)
    except Exception as exc:
        return unexpected_error_response(service_name, route, exc, logger)
