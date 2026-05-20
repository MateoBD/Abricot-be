import json
import logging
import os
from typing import Any, Callable
from urllib import parse, request
from urllib.error import HTTPError, URLError

from app.exceptions.errors import AppError
from app.repositories.user_repository import UserRepository
from app.services.cognito_user_service import CognitoUserService
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


def _redirect(location: str) -> dict:
    return {
        "statusCode": 302,
        "headers": {
            "Location": location,
            "Cache-Control": "no-store",
        },
        "body": "",
    }


def _frontend_error_redirect(code: str, description: str | None = None) -> dict:
    fragment = {"error": code}
    if description:
        fragment["error_description"] = description
    return _redirect(f"{_frontend_callback_url()}#{parse.urlencode(fragment)}")


def _frontend_callback_url() -> str:
    return os.environ["FRONTEND_CALLBACK_URL"].rstrip("/")


def _cognito_domain() -> str:
    domain = os.environ["COGNITO_DOMAIN"].rstrip("/")
    if domain.startswith("https://") or domain.startswith("http://"):
        return domain
    return f"https://{domain}"


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


def _query_params(event: dict) -> dict:
    return event.get("queryStringParameters") or {}


def _path_parameters(event: dict) -> dict:
    return event.get("pathParameters") or {}


def _json_body(event: dict) -> dict:
    raw_body = event.get("body")
    if not raw_body:
        return {}
    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        return {}
    return body if isinstance(body, dict) else {}


def _handle_callback(event: dict) -> dict:
    query = _query_params(event)
    error = query.get("error")
    if error:
        logger.info("oauth_callback_error_received")
        return _frontend_error_redirect(error, query.get("error_description"))

    code = query.get("code")
    if not code:
        logger.warning("oauth_callback_missing_code")
        return _frontend_error_redirect("missing_code")

    token_payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": os.environ["COGNITO_CLIENT_ID"],
        "redirect_uri": os.environ["API_GATEWAY_CALLBACK_URL"],
    }

    body = parse.urlencode(token_payload).encode("utf-8")
    token_request = request.Request(  # noqa: S310
        f"{_cognito_domain()}/oauth2/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with request.urlopen(token_request, timeout=8) as response:  # noqa: S310
            token_response = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        logger.warning("oauth_token_exchange_http_error status=%s", exc.code)
        return _frontend_error_redirect("token_exchange_failed")
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("oauth_token_exchange_failed type=%s", type(exc).__name__)
        return _frontend_error_redirect("token_exchange_failed")

    fragment = {
        "access_token": token_response.get("access_token", ""),
        "id_token": token_response.get("id_token", ""),
        "expires_in": str(token_response.get("expires_in", "")),
    }
    if token_response.get("refresh_token"):
        fragment["refresh_token"] = token_response["refresh_token"]

    fragment = {key: value for key, value in fragment.items() if value}
    logger.info("oauth_token_exchange_succeeded")
    return _redirect(f"{_frontend_callback_url()}#{parse.urlencode(fragment)}")


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


def _claim_email(claims: dict[str, Any]) -> str | None:
    email = claims.get("email")
    if not isinstance(email, str):
        return None
    email = email.strip().lower()
    return email or None


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


def _app_error_response(error: AppError) -> dict:
    payload = {"message": error.public_message or error.message}
    if error.payload:
        payload["errors"] = error.payload
    return _json_response(error.status_code, payload)


def _database_error_response(error: RuntimeError) -> dict:
    logger.warning(
        "users_service_db_configuration_error type=%s",
        str(error).split(":", 1)[0],
    )
    return _json_response(500, {"message": "Users service database is not configured."})


def _unexpected_error_response(route: str, error: Exception) -> dict:
    logger.warning("%s_failed type=%s", route, type(error).__name__)
    return _json_response(500, {"message": "Users service failed."})


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


def _handle_auth_test(event: dict) -> dict:
    claims = _authorizer_claims(event)
    sanitized = {
        "sub": claims.get("sub"),
        "email": claims.get("email"),
        "token_use": claims.get("token_use"),
    }
    groups = _groups_from_claims(claims)
    if groups is not None:
        sanitized["groups"] = groups

    return _json_response(
        200,
        {
            "ok": True,
            "claims": {
                key: value for key, value in sanitized.items() if value is not None
            },
        },
    )


def _handle_post_users(event: dict) -> dict:
    claims = _authorizer_claims(event)
    body = _json_body(event)

    def operation() -> tuple[int, dict]:
        CognitoUserService.reject_privilege_fields(body)
        cognito_sub = _claim_sub(claims)
        existing = (
            UserRepository.get_by_cognito_sub(cognito_sub) if cognito_sub else None
        )
        account_type = CognitoUserService.parse_account_type(
            body,
            required=existing is None,
        )
        result = CognitoUserService.provision_user(
            cognito_sub=cognito_sub,
            email=_claim_email(claims),
            given_name=claims.get("given_name"),
            family_name=claims.get("family_name"),
            account_type=account_type,
        )
        return (201 if result.created else 200), result.user

    return _with_backend("users_post", operation)


def _is_user_restaurants_list(event: dict) -> bool:
    params = _path_parameters(event)
    if params.get("userId") and "restaurants" in _route_path(event):
        return True
    parts = _route_path(event).strip("/").split("/")
    return len(parts) == 3 and parts[0] == "users" and parts[2] == "restaurants"


def _user_restaurants_user_id(event: dict) -> str | None:
    params = _path_parameters(event)
    if params.get("userId"):
        return str(params["userId"])
    parts = _route_path(event).strip("/").split("/")
    if len(parts) == 3 and parts[0] == "users" and parts[2] == "restaurants":
        return parts[1] or None
    return None


def _handle_get_user_restaurants(event: dict) -> dict:
    user_id = _user_restaurants_user_id(event)
    if not user_id:
        return _json_response(400, {"message": "Missing user id."})

    claims = _authorizer_claims(event)

    def operation() -> tuple[int, dict]:
        return 200, CognitoUserService.list_restaurants_for_principal(
            user_id=user_id,
            cognito_sub=_claim_sub(claims),
            is_cognito_admin=_is_admin(claims),
        )

    return _with_backend("users_restaurants_list", operation)


def _path_user_id(event: dict) -> str | None:
    params = _path_parameters(event)
    if params.get("userId"):
        return str(params["userId"])

    path = _route_path(event).strip("/")
    parts = path.split("/")
    if len(parts) == 2 and parts[0] == "users":
        return parts[1]
    return None


def _handle_get_user(event: dict) -> dict:
    user_id = _path_user_id(event)
    if not user_id:
        return _json_response(400, {"message": "Missing user id."})

    claims = _authorizer_claims(event)

    def operation() -> tuple[int, dict]:
        return 200, CognitoUserService.get_profile_for_principal(
            user_id=user_id,
            cognito_sub=_claim_sub(claims),
            is_cognito_admin=_is_admin(claims),
        )

    return _with_backend("users_get", operation)


def _handle_put_user(event: dict) -> dict:
    user_id = _path_user_id(event)
    if not user_id:
        return _json_response(400, {"message": "Missing user id."})

    claims = _authorizer_claims(event)

    def operation() -> tuple[int, dict]:
        return 200, CognitoUserService.update_profile_for_principal(
            user_id=user_id,
            cognito_sub=_claim_sub(claims),
            data=_json_body(event),
            is_cognito_admin=_is_admin(claims),
        )

    return _with_backend("users_put", operation)


def handler(event, context):
    event = event or {}
    path = _route_path(event)
    method = _method(event)

    if method == "GET" and path.endswith("/callback"):
        return _handle_callback(event)

    if method == "GET" and path.endswith("/auth-test"):
        return _handle_auth_test(event)

    if method == "POST" and path.rstrip("/") == "/users":
        return _handle_post_users(event)

    if method == "GET" and _is_user_restaurants_list(event):
        return _handle_get_user_restaurants(event)

    if method == "GET" and "/users/" in path:
        return _handle_get_user(event)

    if method == "PUT" and "/users/" in path:
        return _handle_put_user(event)

    return _json_response(404, {"message": "Route not found."})
