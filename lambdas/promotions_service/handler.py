import logging

from app.services.cognito_promotion_service import CognitoPromotionService
from common.api import (
    authorizer_claims,
    claim_sub,
    is_cognito_super_admin,
    json_body,
    method,
    path_parameters,
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


def _promotion_id(event: dict) -> str | None:
    params = path_parameters(event)
    if params.get("promotionId"):
        return params["promotionId"]
    parts = _path_parts(event)
    if len(parts) == 4 and parts[0] == "restaurants" and parts[2] == "promotions":
        return parts[3]
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
        and path == f"/restaurants/{restaurant_id}/promotions"
    ):
        return with_backend(
            "promotions_service",
            "promotions_list",
            lambda: (
                200,
                CognitoPromotionService.list_for_restaurant(
                    restaurant_id=restaurant_id,
                    **auth,
                ),
            ),
            logger,
        )

    if (
        restaurant_id
        and http_method == "POST"
        and path == f"/restaurants/{restaurant_id}/promotions"
    ):
        return with_backend(
            "promotions_service",
            "promotions_create",
            lambda: (
                201,
                CognitoPromotionService.create(
                    restaurant_id=restaurant_id,
                    body=json_body(event),
                    **auth,
                ),
            ),
            logger,
        )

    promotion_id = _promotion_id(event)
    if (
        restaurant_id
        and promotion_id
        and http_method == "GET"
        and path == f"/restaurants/{restaurant_id}/promotions/{promotion_id}"
    ):
        return with_backend(
            "promotions_service",
            "promotions_get",
            lambda: (
                200,
                CognitoPromotionService.get_by_id(
                    restaurant_id=restaurant_id,
                    promotion_id=promotion_id,
                    **auth,
                ),
            ),
            logger,
        )

    if (
        restaurant_id
        and promotion_id
        and http_method == "DELETE"
        and path == f"/restaurants/{restaurant_id}/promotions/{promotion_id}"
    ):
        def operation():
            CognitoPromotionService.delete(
                restaurant_id=restaurant_id,
                promotion_id=promotion_id,
                **auth,
            )
            return 204, None

        return with_backend("promotions_service", "promotions_delete", operation, logger)

    return route_not_found()
