import json
import logging
import os
from typing import Any
from urllib import parse, request
from urllib.error import HTTPError, URLError
from uuid import uuid4

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
        return json.loads(raw_body)
    except json.JSONDecodeError:
        return {}


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


def _claim_sub(claims: dict[str, Any]) -> str | None:
    sub = claims.get("sub")
    return str(sub).strip() if sub else None


def _claim_email(claims: dict[str, Any]) -> str | None:
    email = claims.get("email")
    if not isinstance(email, str):
        return None
    email = email.strip().lower()
    return email or None


def _is_admin(claims: dict[str, Any]) -> bool:
    groups = _groups_from_claims(claims) or []
    return "SUPER_ADMIN" in groups


def _db_required_env() -> list[str]:
    return [
        "POSTGRES_HOST",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ]


def _db_missing_env() -> list[str]:
    return [name for name in _db_required_env() if not os.environ.get(name)]


def _db_connect():
    missing = _db_missing_env()
    if missing:
        raise RuntimeError(f"missing_db_env:{','.join(missing)}")

    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError as exc:
        raise RuntimeError("missing_psycopg2_dependency") from exc

    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        sslmode=os.environ.get("POSTGRES_SSLMODE", "prefer"),
        connect_timeout=5,
        cursor_factory=RealDictCursor,
    )


def _user_payload(row: dict[str, Any]) -> dict:
    created_at = row.get("created_at")
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()

    return {
        "id": str(row["id"]),
        "email": row["email"],
        "name": row["name"],
        "surname": row["surname"],
        "role": row["role"],
        "createdAt": created_at,
    }


def _get_user_by_cognito_sub(conn, cognito_sub: str) -> dict[str, Any] | None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, email, name, surname, role, cognito_sub, created_at
            FROM users
            WHERE cognito_sub = %s
            """,
            (cognito_sub,),
        )
        return cursor.fetchone()


def _get_user_by_email(conn, email: str) -> dict[str, Any] | None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, email, name, surname, role, cognito_sub, created_at
            FROM users
            WHERE lower(email) = lower(%s)
            """,
            (email,),
        )
        return cursor.fetchone()


def _get_user_by_id(conn, user_id: str) -> dict[str, Any] | None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, email, name, surname, role, cognito_sub, created_at
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        )
        return cursor.fetchone()


def _link_user_to_cognito_sub(conn, user_id: str, cognito_sub: str) -> dict[str, Any]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE users
            SET cognito_sub = %s
            WHERE id = %s
            RETURNING id, email, name, surname, role, cognito_sub, created_at
            """,
            (cognito_sub, user_id),
        )
        row = cursor.fetchone()
    conn.commit()
    return row


def _create_cognito_user(
    conn,
    *,
    cognito_sub: str,
    email: str,
    name: str,
    surname: str,
) -> dict[str, Any]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO users (id, email, cognito_sub, password_hash, name, surname, role, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'CUSTOMER', now())
            RETURNING id, email, name, surname, role, cognito_sub, created_at
            """,
            (
                str(uuid4()),
                email,
                cognito_sub,
                f"COGNITO_ONLY:{cognito_sub}",
                name,
                surname,
            ),
        )
        row = cursor.fetchone()
    conn.commit()
    return row


def _update_user_profile(conn, user_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
    allowed: dict[str, str] = {}
    for api_name, column in (("name", "name"), ("surname", "surname")):
        value = data.get(api_name)
        if value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            raise ValueError(api_name)
        allowed[column] = value.strip()

    if not allowed:
        return _get_user_by_id(conn, user_id)

    assignments = ", ".join(f"{column} = %s" for column in allowed)
    values = [*allowed.values(), user_id]
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE users
            SET {assignments}
            WHERE id = %s
            RETURNING id, email, name, surname, role, cognito_sub, created_at
            """,
            values,
        )
        row = cursor.fetchone()
    conn.commit()
    return row


def _principal_user(conn, claims: dict[str, Any]) -> dict[str, Any] | None:
    cognito_sub = _claim_sub(claims)
    if not cognito_sub:
        return None
    return _get_user_by_cognito_sub(conn, cognito_sub)


def _require_same_user_or_admin(
    principal: dict[str, Any] | None,
    claims: dict[str, Any],
    user_id: str,
) -> bool:
    if not principal:
        return False
    return (
        str(principal["id"]) == user_id
        or principal.get("role") == "SUPER_ADMIN"
        or _is_admin(claims)
    )


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


def _handle_post_users(event: dict) -> dict:
    claims = _authorizer_claims(event)
    cognito_sub = _claim_sub(claims)
    if not cognito_sub:
        return _json_response(401, {"message": "Missing Cognito sub claim."})

    email = _claim_email(claims)
    if not email:
        return _json_response(
            400,
            {
                "message": "Email claim is required for first Cognito provisioning. Use the ID token for POST /users.",
            },
        )

    name = str(claims.get("given_name") or email.split("@", 1)[0]).strip() or "Cognito"
    surname = str(claims.get("family_name") or "User").strip() or "User"

    try:
        with _db_connect() as conn:
            user = _get_user_by_cognito_sub(conn, cognito_sub)
            if user:
                return _json_response(200, _user_payload(user))

            user = _get_user_by_email(conn, email)
            if user:
                linked_sub = user.get("cognito_sub")
                if linked_sub and linked_sub != cognito_sub:
                    return _json_response(409, {"message": "Email is already linked to another Cognito user."})
                return _json_response(
                    200,
                    _user_payload(_link_user_to_cognito_sub(conn, str(user["id"]), cognito_sub)),
                )

            return _json_response(
                201,
                _user_payload(
                    _create_cognito_user(
                        conn,
                        cognito_sub=cognito_sub,
                        email=email,
                        name=name,
                        surname=surname,
                    )
                ),
            )
    except RuntimeError as exc:
        logger.warning("users_post_runtime_error type=%s", str(exc).split(":", 1)[0])
        return _json_response(500, {"message": "Users service database is not configured."})
    except Exception as exc:
        logger.warning("users_post_failed type=%s", type(exc).__name__)
        return _json_response(500, {"message": "Users service failed."})


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
    try:
        with _db_connect() as conn:
            principal = _principal_user(conn, claims)
            if not _require_same_user_or_admin(principal, claims, user_id):
                return _json_response(403, {"message": "Forbidden."})

            user = _get_user_by_id(conn, user_id)
            if not user:
                return _json_response(404, {"message": "User not found."})
            return _json_response(200, _user_payload(user))
    except RuntimeError as exc:
        logger.warning("users_get_runtime_error type=%s", str(exc).split(":", 1)[0])
        return _json_response(500, {"message": "Users service database is not configured."})
    except Exception as exc:
        logger.warning("users_get_failed type=%s", type(exc).__name__)
        return _json_response(500, {"message": "Users service failed."})


def _handle_put_user(event: dict) -> dict:
    user_id = _path_user_id(event)
    if not user_id:
        return _json_response(400, {"message": "Missing user id."})

    claims = _authorizer_claims(event)
    try:
        with _db_connect() as conn:
            principal = _principal_user(conn, claims)
            if not _require_same_user_or_admin(principal, claims, user_id):
                return _json_response(403, {"message": "Forbidden."})

            try:
                user = _update_user_profile(conn, user_id, _json_body(event))
            except ValueError as exc:
                return _json_response(400, {"message": f"Invalid {exc.args[0]}."})

            if not user:
                return _json_response(404, {"message": "User not found."})
            return _json_response(200, _user_payload(user))
    except RuntimeError as exc:
        logger.warning("users_put_runtime_error type=%s", str(exc).split(":", 1)[0])
        return _json_response(500, {"message": "Users service database is not configured."})
    except Exception as exc:
        logger.warning("users_put_failed type=%s", type(exc).__name__)
        return _json_response(500, {"message": "Users service failed."})


def handler(event, context):
    path = _route_path(event)
    method = _method(event)

    if method == "GET" and path.endswith("/callback"):
        return _handle_callback(event)

    if method == "GET" and path.endswith("/auth-test"):
        return _handle_auth_test(event)

    if method == "POST" and path.endswith("/users"):
        return _handle_post_users(event)

    if method == "GET" and "/users/" in path:
        return _handle_get_user(event)

    if method == "PUT" and "/users/" in path:
        return _handle_put_user(event)

    return _json_response(404, {"message": "Route not found."})
