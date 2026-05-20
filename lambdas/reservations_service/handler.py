import logging

from app.services.cognito_reservation_service import CognitoReservationService
from common.api import (
    authorizer_claims,
    claim_sub,
    is_cognito_super_admin,
    json_body,
    method,
    path_parameters,
    query_params,
    route_not_found,
    route_path,
    with_backend,
)

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
        return with_backend(
            "reservations_service",
            "reservations_create",
            lambda: (
                201,
                CognitoReservationService.create(
                    restaurant_id=restaurant_id,
                    body=json_body(event),
                    **auth,
                ),
            ),
            logger,
        )

    if (
        restaurant_id
        and http_method == "POST"
        and path == f"/restaurants/{restaurant_id}/public-reservations"
    ):
        return with_backend(
            "reservations_service",
            "reservations_create_public",
            lambda: (
                201,
                CognitoReservationService.create_public(
                    restaurant_id=restaurant_id,
                    body=json_body(event),
                ),
            ),
            logger,
        )

    if (
        restaurant_id
        and http_method == "GET"
        and path == f"/restaurants/{restaurant_id}/reservations"
    ):
        return with_backend(
            "reservations_service",
            "reservations_restaurant_list",
            lambda: (
                200,
                CognitoReservationService.list_for_restaurant(
                    restaurant_id=restaurant_id,
                    query=query,
                    **auth,
                ),
            ),
            logger,
        )

    reservation_id = _reservation_id(event)
    if reservation_id and http_method == "GET" and path == f"/reservations/{reservation_id}":
        return with_backend(
            "reservations_service",
            "reservations_get",
            lambda: (
                200,
                CognitoReservationService.get_by_id(
                    reservation_id=reservation_id,
                    cognito_sub=auth["cognito_sub"],
                ),
            ),
            logger,
        )

    if reservation_id and http_method == "PATCH" and path == f"/reservations/{reservation_id}":
        return with_backend(
            "reservations_service",
            "reservations_patch",
            lambda: (
                200,
                CognitoReservationService.transition_status(
                    reservation_id=reservation_id,
                    cognito_sub=auth["cognito_sub"],
                    body=json_body(event),
                ),
            ),
            logger,
        )

    user_id = _user_id(event)
    if user_id and http_method == "GET" and path == f"/users/{user_id}/reservations":
        return with_backend(
            "reservations_service",
            "reservations_user_list",
            lambda: (
                200,
                CognitoReservationService.list_for_user(
                    user_id=user_id,
                    query=query,
                    **auth,
                ),
            ),
            logger,
        )

    return route_not_found()
