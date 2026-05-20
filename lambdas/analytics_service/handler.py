import logging

from app.services.cognito_analytics_service import CognitoAnalyticsService
from common.api import (
    authorizer_claims,
    claim_sub,
    is_cognito_super_admin,
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


def _restaurant_id(event: dict) -> str | None:
    params = path_parameters(event)
    if params.get("restaurantId"):
        return params["restaurantId"]
    parts = route_path(event).rstrip("/").strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "restaurants":
        return parts[1]
    return None


def handler(event, context):
    event = event or {}
    http_method = method(event)
    path = route_path(event).rstrip("/")
    auth = _auth_kwargs(event)
    restaurant_id = _restaurant_id(event)

    if (
        restaurant_id
        and http_method == "GET"
        and path == f"/restaurants/{restaurant_id}/analytics"
    ):
        return with_backend(
            "analytics_service",
            "analytics_get",
            lambda: (
                200,
                CognitoAnalyticsService.get_report(
                    restaurant_id=restaurant_id,
                    query=query_params(event),
                    **auth,
                ),
            ),
            logger,
        )

    return route_not_found()
