import json
import logging
import os
from typing import Any
from urllib import parse, request
from urllib.error import HTTPError, URLError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _json_response(status_code: int, payload: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(payload),
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
    token_request = request.Request(
        f"{_cognito_domain()}/oauth2/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with request.urlopen(token_request, timeout=8) as response:
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


def _groups_from_claims(claims: dict[str, Any]) -> list[str] | None:
    groups = claims.get("cognito:groups") or claims.get("groups")
    if groups is None:
        return None
    if isinstance(groups, list):
        return [str(group) for group in groups]
    if isinstance(groups, str):
        return [group for group in groups.split(",") if group]
    return [str(groups)]


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
            "claims": {key: value for key, value in sanitized.items() if value is not None},
        },
    )


def handler(event, context):
    path = _route_path(event)
    method = _method(event)

    if method != "GET":
        return _json_response(405, {"message": "Method not allowed."})

    if path.endswith("/callback"):
        return _handle_callback(event)

    if path.endswith("/auth-test"):
        return _handle_auth_test(event)

    return _json_response(404, {"message": "Route not found."})
