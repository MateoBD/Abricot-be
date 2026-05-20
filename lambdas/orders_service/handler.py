import json
import logging
from typing import Any, Callable

from app.exceptions.errors import AppError
from app.services.cognito_order_service import CognitoOrderService
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


def _query_params(event: dict) -> dict[str, str]:
    raw = event.get("queryStringParameters") or {}
    return {key: str(value) for key, value in raw.items() if value is not None}


def _path_parameters(event: dict) -> dict[str, str]:
    raw = event.get("pathParameters") or {}
    return {key: str(value) for key, value in raw.items() if value is not None}


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


def _groups_from_claims(claims: dict[str, Any]) -> list[str] | None:
    groups = claims.get("cognito:groups") or claims.get("groups")
    if groups is None:
        return None
    if isinstance(groups, list):
        return [str(group) for group in groups]
    if isinstance(groups, str):
        return [group for group in groups.split(",") if group]
    return [str(groups)]


def _is_admin(claims: dict[str, Any]) -> bool:
    groups = _groups_from_claims(claims) or []
    return "SUPER_ADMIN" in groups


def _int_query(query: dict[str, str], name: str, default: int) -> int:
    try:
        return int(query.get(name, str(default)))
    except ValueError:
        return default


def _app_error_response(error: AppError) -> dict:
    payload = {"message": error.public_message or error.message}
    if error.payload:
        payload["errors"] = error.payload
    return _json_response(error.status_code, payload)


def _database_error_response(error: RuntimeError) -> dict:
    logger.warning(
        "orders_service_db_configuration_error type=%s",
        str(error).split(":", 1)[0],
    )
    return _json_response(500, {"message": "Orders service database is not configured."})


def _unexpected_error_response(route: str, error: Exception) -> dict:
    logger.warning("%s_failed type=%s", route, type(error).__name__)
    return _json_response(500, {"message": "Orders service failed."})


def _with_backend(route: str, operation: Callable[[], tuple[int, dict]]) -> dict:
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


def _restaurant_order_path(event: dict) -> tuple[str | None, str | None]:
    params = _path_parameters(event)
    restaurant_id = params.get("restaurantId")
    order_id = params.get("orderId")
    if restaurant_id:
        return restaurant_id, order_id

    parts = _route_path(event).strip("/").split("/")
    if len(parts) < 3 or parts[0] != "restaurants" or parts[2] != "orders":
        return None, None
    return parts[1] or None, parts[3] if len(parts) >= 4 else None


def _user_orders_user_id(event: dict) -> str | None:
    params = _path_parameters(event)
    if params.get("userId"):
        return params["userId"]

    parts = _route_path(event).strip("/").split("/")
    if len(parts) == 3 and parts[0] == "users" and parts[2] == "orders":
        return parts[1] or None
    return None


def _is_restaurant_orders_collection(event: dict) -> bool:
    parts = _route_path(event).strip("/").split("/")
    return len(parts) == 3 and parts[0] == "restaurants" and parts[2] == "orders"


def _is_restaurant_order_detail(event: dict) -> bool:
    parts = _route_path(event).strip("/").split("/")
    return len(parts) == 4 and parts[0] == "restaurants" and parts[2] == "orders"


def _is_user_orders_collection(event: dict) -> bool:
    parts = _route_path(event).strip("/").split("/")
    return len(parts) == 3 and parts[0] == "users" and parts[2] == "orders"


def _handle_create_order(event: dict) -> dict:
    restaurant_id, _ = _restaurant_order_path(event)
    if not restaurant_id:
        return _json_response(400, {"message": "Missing restaurant id."})

    claims = _authorizer_claims(event)

    def operation() -> tuple[int, dict]:
        return 201, CognitoOrderService.create_order(
            restaurant_id=restaurant_id,
            cognito_sub=_claim_sub(claims),
            body=_json_body(event),
        )

    return _with_backend("orders_create", operation)


def _handle_list_user_orders(event: dict) -> dict:
    user_id = _user_orders_user_id(event)
    if not user_id:
        return _json_response(400, {"message": "Missing user id."})

    claims = _authorizer_claims(event)
    query = _query_params(event)

    def operation() -> tuple[int, dict]:
        return 200, CognitoOrderService.list_user_orders(
            user_id=user_id,
            cognito_sub=_claim_sub(claims),
            is_cognito_admin=_is_admin(claims),
            page=_int_query(query, "page", 1),
            per_page=_int_query(query, "perPage", 20),
        )

    return _with_backend("orders_user_list", operation)


def _handle_list_restaurant_orders(event: dict) -> dict:
    restaurant_id, _ = _restaurant_order_path(event)
    if not restaurant_id:
        return _json_response(400, {"message": "Missing restaurant id."})

    claims = _authorizer_claims(event)
    query = _query_params(event)

    def operation() -> tuple[int, dict]:
        return 200, CognitoOrderService.list_restaurant_orders(
            restaurant_id=restaurant_id,
            cognito_sub=_claim_sub(claims),
            is_cognito_admin=_is_admin(claims),
            status_filter=query.get("status"),
            page=_int_query(query, "page", 1),
            per_page=_int_query(query, "perPage", 20),
        )

    return _with_backend("orders_restaurant_list", operation)


def _handle_get_restaurant_order(event: dict) -> dict:
    restaurant_id, order_id = _restaurant_order_path(event)
    if not restaurant_id or not order_id:
        return _json_response(400, {"message": "Missing restaurant id or order id."})

    claims = _authorizer_claims(event)

    def operation() -> tuple[int, dict]:
        return 200, CognitoOrderService.get_restaurant_order(
            restaurant_id=restaurant_id,
            order_id=order_id,
            cognito_sub=_claim_sub(claims),
            is_cognito_admin=_is_admin(claims),
        )

    return _with_backend("orders_restaurant_detail", operation)


def _handle_patch_restaurant_order(event: dict) -> dict:
    restaurant_id, order_id = _restaurant_order_path(event)
    if not restaurant_id or not order_id:
        return _json_response(400, {"message": "Missing restaurant id or order id."})

    claims = _authorizer_claims(event)

    def operation() -> tuple[int, dict]:
        return 200, CognitoOrderService.patch_restaurant_order(
            restaurant_id=restaurant_id,
            order_id=order_id,
            cognito_sub=_claim_sub(claims),
            body=_json_body(event),
            is_cognito_admin=_is_admin(claims),
        )

    return _with_backend("orders_restaurant_patch", operation)


def handler(event, context):
    event = event or {}
    method = _method(event)

    if method == "POST" and _is_restaurant_orders_collection(event):
        return _handle_create_order(event)

    if method == "GET" and _is_user_orders_collection(event):
        return _handle_list_user_orders(event)

    if method == "GET" and _is_restaurant_orders_collection(event):
        return _handle_list_restaurant_orders(event)

    if method == "GET" and _is_restaurant_order_detail(event):
        return _handle_get_restaurant_order(event)

    if method == "PATCH" and _is_restaurant_order_detail(event):
        return _handle_patch_restaurant_order(event)

    return _json_response(404, {"message": "Route not found."})
