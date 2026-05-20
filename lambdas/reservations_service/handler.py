import logging

from app.exceptions.errors import AppError
from app.services.cognito_reservation_service import CognitoReservationService
from common.api import (
    app_error_response,
    authorizer_claims,
    claim_sub,
    database_error_response,
    is_cognito_super_admin,
    json_body,
    json_response,
    method,
    path_parameters,
    query_params,
    route_not_found,
    route_path,
)
from common.flask_db import backend_app_context

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _auth_kwargs(event: dict) -> dict:
    claims = authorizer_claims(event)
    return {
        "cognito_sub": claim_sub(claims),
        "is_cognito_admin": is_cognito_super_admin(claims),
    }


def _path_parts(event: dict) -> list[str]:
    return route_path(event).rstrip("/").strip("/").split("/")


def _restaurant_id(event: dict) -> str | None:
    params = path_parameters(event)
    if params.get("restaurantId"):
        return params["restaurantId"]
    parts = _path_parts(event)
    if len(parts) >= 2 and parts[0] == "restaurants":
        return parts[1]
    return None


def _reservation_id(event: dict) -> str | None:
    params = path_parameters(event)
    if params.get("reservationId"):
        return params["reservationId"]
    parts = _path_parts(event)
    if len(parts) == 2 and parts[0] == "reservations":
        return parts[1]
    return None


def _user_id(event: dict) -> str | None:
    params = path_parameters(event)
    if params.get("userId"):
        return params["userId"]
    parts = _path_parts(event)
    if len(parts) == 3 and parts[0] == "users" and parts[2] == "reservations":
        return parts[1]
    return None


def _body_keys(body: dict | None) -> list[str] | None:
    if not isinstance(body, dict):
        return None
    return sorted(str(key) for key in body.keys())


def _internal_error_response() -> dict:
    return json_response(
        500,
        {
            "message": "Reservations service failed.",
            "code": "INTERNAL_ERROR",
            "errors": {},
        },
    )


def _log_unexpected(
    event: dict,
    body: dict | None,
    restaurant_id: str | None,
    route: str,
    error: Exception,
) -> None:
    claims = authorizer_claims(event)
    logger.exception(
        (
            "Reservations service failed: route=%s method=%s path=%s route_key=%s "
            "path_params=%s body_keys=%s restaurant_id=%s cognito_sub_present=%s "
            "error_type=%s"
        ),
        route,
        method(event),
        route_path(event),
        event.get("routeKey"),
        path_parameters(event),
        _body_keys(body),
        restaurant_id,
        bool(claim_sub(claims)),
        type(error).__name__,
    )


def _with_reservations_backend(
    event: dict,
    *,
    route: str,
    operation,
    body: dict | None = None,
    restaurant_id: str | None = None,
) -> dict:
    try:
        with backend_app_context():
            status_code, payload = operation()
            return json_response(status_code, payload)
    except AppError as exc:
        return app_error_response(exc)
    except RuntimeError as exc:
        if str(exc).startswith(("missing_db_env", "invalid_db_target")):
            return database_error_response("reservations_service", exc, logger)
        _log_unexpected(event, body, restaurant_id, route, exc)
        return _internal_error_response()
    except Exception as exc:
        _log_unexpected(event, body, restaurant_id, route, exc)
        return _internal_error_response()


def handler(event, context):
    event = event or {}
    http_method = method(event)
    path = route_path(event).rstrip("/")
    auth = _auth_kwargs(event)
    restaurant_id = _restaurant_id(event)
    query = query_params(event)

    if (
        restaurant_id
        and http_method == "POST"
        and path == f"/restaurants/{restaurant_id}/reservations"
    ):
        body = json_body(event)
        return _with_reservations_backend(
            event,
            route="reservations_create",
            operation=lambda: (
                201,
                CognitoReservationService.create(
                    restaurant_id=restaurant_id,
                    body=body,
                    **auth,
                ),
            ),
            body=body,
            restaurant_id=restaurant_id,
        )

    if (
        restaurant_id
        and http_method == "POST"
        and path == f"/restaurants/{restaurant_id}/public-reservations"
    ):
        body = json_body(event)
        return _with_reservations_backend(
            event,
            route="reservations_create_public",
            operation=lambda: (
                201,
                CognitoReservationService.create_public(
                    restaurant_id=restaurant_id,
                    body=body,
                ),
            ),
            body=body,
            restaurant_id=restaurant_id,
        )

    if (
        restaurant_id
        and http_method == "GET"
        and path == f"/restaurants/{restaurant_id}/reservations"
    ):
        return _with_reservations_backend(
            event,
            route="reservations_restaurant_list",
            operation=lambda: (
                200,
                CognitoReservationService.list_for_restaurant(
                    restaurant_id=restaurant_id,
                    query=query,
                    **auth,
                ),
            ),
            restaurant_id=restaurant_id,
        )

    reservation_id = _reservation_id(event)
    if reservation_id and http_method == "GET" and path == f"/reservations/{reservation_id}":
        return _with_reservations_backend(
            event,
            route="reservations_get",
            operation=lambda: (
                200,
                CognitoReservationService.get_by_id(
                    reservation_id=reservation_id,
                    cognito_sub=auth["cognito_sub"],
                ),
            ),
        )

    if reservation_id and http_method == "PATCH" and path == f"/reservations/{reservation_id}":
        body = json_body(event)
        return _with_reservations_backend(
            event,
            route="reservations_patch",
            operation=lambda: (
                200,
                CognitoReservationService.transition_status(
                    reservation_id=reservation_id,
                    cognito_sub=auth["cognito_sub"],
                    body=body,
                ),
            ),
            body=body,
        )

    user_id = _user_id(event)
    if user_id and http_method == "GET" and path == f"/users/{user_id}/reservations":
        return _with_reservations_backend(
            event,
            route="reservations_user_list",
            operation=lambda: (
                200,
                CognitoReservationService.list_for_user(
                    user_id=user_id,
                    query=query,
                    **auth,
                ),
            ),
        )

    return route_not_found()
