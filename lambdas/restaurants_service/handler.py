import logging

from app.services.cognito_restaurant_service import CognitoRestaurantService
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
    return parts[1] if len(parts) >= 2 and parts[0] == "restaurants" else None


def _menu_id(event: dict) -> str | None:
    params = path_parameters(event)
    if params.get("menuId"):
        return params["menuId"]
    parts = _path_parts(event)
    if len(parts) >= 4 and parts[0] == "restaurants" and parts[2] == "menus":
        return parts[3]
    if len(parts) >= 5 and parts[0] == "restaurants" and parts[2] == "admin" and parts[3] == "menus":
        return parts[4]
    return None


def _category_id(event: dict) -> str | None:
    params = path_parameters(event)
    if params.get("categoryId"):
        return params["categoryId"]
    parts = _path_parts(event)
    if len(parts) >= 6 and parts[0] == "restaurants" and parts[2] == "menus" and parts[4] == "categories":
        return parts[5]
    return None


def _item_id(event: dict) -> str | None:
    params = path_parameters(event)
    if params.get("itemId"):
        return params["itemId"]
    parts = _path_parts(event)
    if len(parts) >= 8 and parts[6] == "items":
        return parts[7]
    return None


def _table_id(event: dict) -> str | None:
    params = path_parameters(event)
    if params.get("tableId"):
        return params["tableId"]
    parts = _path_parts(event)
    if len(parts) == 4 and parts[0] == "restaurants" and parts[2] == "tables":
        return parts[3]
    return None


def _user_id_from_reviews(event: dict) -> str | None:
    params = path_parameters(event)
    if params.get("userId"):
        return params["userId"]
    parts = _path_parts(event)
    if len(parts) == 4 and parts[0] == "restaurants" and parts[2] == "reviews":
        return parts[3]
    return None


def _admin_user_id(event: dict) -> str | None:
    params = path_parameters(event)
    if params.get("userId"):
        return params["userId"]
    parts = _path_parts(event)
    if len(parts) == 4 and parts[0] == "restaurants" and parts[2] == "admins":
        return parts[3]
    return None


def _is_admin_menus_collection(event: dict) -> bool:
    parts = _path_parts(event)
    return (
        len(parts) == 4
        and parts[0] == "restaurants"
        and parts[2] == "admin"
        and parts[3] == "menus"
    )


def _is_admin_menu_detail(event: dict) -> bool:
    parts = _path_parts(event)
    return (
        len(parts) == 5
        and parts[0] == "restaurants"
        and parts[2] == "admin"
        and parts[3] == "menus"
    )


def _is_menu_categories_collection(event: dict) -> bool:
    parts = _path_parts(event)
    return (
        len(parts) == 5
        and parts[0] == "restaurants"
        and parts[2] == "menus"
        and parts[4] == "categories"
    )


def _is_menu_category_detail(event: dict) -> bool:
    parts = _path_parts(event)
    return (
        len(parts) == 6
        and parts[0] == "restaurants"
        and parts[2] == "menus"
        and parts[4] == "categories"
    )


def _is_menu_items_collection(event: dict) -> bool:
    parts = _path_parts(event)
    return (
        len(parts) == 7
        and parts[0] == "restaurants"
        and parts[2] == "menus"
        and parts[4] == "categories"
        and parts[6] == "items"
    )


def _is_menu_item_detail(event: dict) -> bool:
    parts = _path_parts(event)
    return (
        len(parts) == 8
        and parts[0] == "restaurants"
        and parts[2] == "menus"
        and parts[4] == "categories"
        and parts[6] == "items"
    )


def handler(event, context):
    event = event or {}
    http_method = method(event)
    path = route_path(event).rstrip("/")
    auth = _auth_kwargs(event)
    restaurant_id = _restaurant_id(event)

    if http_method == "POST" and path == "/restaurants":
        return with_backend(
            "restaurants_service",
            "restaurants_post",
            lambda: (
                201,
                CognitoRestaurantService.create_restaurant(
                    cognito_sub=auth["cognito_sub"],
                    body=json_body(event),
                ),
            ),
            logger,
        )

    if restaurant_id and http_method == "PUT" and path == f"/restaurants/{restaurant_id}":
        return with_backend(
            "restaurants_service",
            "restaurants_put",
            lambda: (
                200,
                CognitoRestaurantService.update_restaurant(
                    restaurant_id=restaurant_id,
                    body=json_body(event),
                    **auth,
                ),
            ),
            logger,
        )

    if restaurant_id and http_method == "DELETE" and path == f"/restaurants/{restaurant_id}":
        def operation():
            CognitoRestaurantService.delete_restaurant(restaurant_id=restaurant_id, **auth)
            return 204, None

        return with_backend("restaurants_service", "restaurants_delete", operation, logger)

    user_id = _user_id_from_reviews(event)
    if (
        restaurant_id
        and user_id
        and http_method == "PUT"
        and path == f"/restaurants/{restaurant_id}/reviews/{user_id}"
    ):
        return with_backend(
            "restaurants_service",
            "restaurants_review_put",
            lambda: (
                200,
                CognitoRestaurantService.put_review(
                    restaurant_id=restaurant_id,
                    user_id=user_id,
                    body=json_body(event),
                    **auth,
                ),
            ),
            logger,
        )

    if restaurant_id and http_method == "GET" and path == f"/restaurants/{restaurant_id}/admins":
        return with_backend(
            "restaurants_service",
            "restaurants_admins_list",
            lambda: (200, CognitoRestaurantService.list_admins(restaurant_id=restaurant_id, **auth)),
            logger,
        )

    if restaurant_id and http_method == "POST" and path == f"/restaurants/{restaurant_id}/admins":
        return with_backend(
            "restaurants_service",
            "restaurants_admins_post",
            lambda: (
                201,
                CognitoRestaurantService.add_admin(
                    restaurant_id=restaurant_id,
                    body=json_body(event),
                    **auth,
                ),
            ),
            logger,
        )

    admin_user_id = _admin_user_id(event)
    if (
        restaurant_id
        and admin_user_id
        and http_method == "DELETE"
        and path == f"/restaurants/{restaurant_id}/admins/{admin_user_id}"
    ):
        def operation():
            CognitoRestaurantService.remove_admin(
                restaurant_id=restaurant_id,
                user_id=admin_user_id,
                **auth,
            )
            return 204, None

        return with_backend("restaurants_service", "restaurants_admins_delete", operation, logger)

    if restaurant_id and http_method == "GET" and _is_admin_menus_collection(event):
        return with_backend(
            "restaurants_service",
            "restaurants_admin_menus_list",
            lambda: (200, CognitoRestaurantService.list_admin_menus(restaurant_id=restaurant_id, **auth)),
            logger,
        )

    if restaurant_id and http_method == "POST" and _is_admin_menus_collection(event):
        return with_backend(
            "restaurants_service",
            "restaurants_admin_menus_post",
            lambda: (
                201,
                CognitoRestaurantService.create_admin_menu(
                    restaurant_id=restaurant_id,
                    body=json_body(event),
                    **auth,
                ),
            ),
            logger,
        )

    menu_id = _menu_id(event)
    if restaurant_id and menu_id and http_method == "GET" and _is_admin_menu_detail(event):
        return with_backend(
            "restaurants_service",
            "restaurants_admin_menu_get",
            lambda: (
                200,
                CognitoRestaurantService.get_admin_menu(
                    restaurant_id=restaurant_id,
                    menu_id=menu_id,
                    **auth,
                ),
            ),
            logger,
        )

    if restaurant_id and menu_id and http_method == "PUT" and _is_admin_menu_detail(event):
        return with_backend(
            "restaurants_service",
            "restaurants_admin_menu_put",
            lambda: (
                200,
                CognitoRestaurantService.update_admin_menu(
                    restaurant_id=restaurant_id,
                    menu_id=menu_id,
                    body=json_body(event),
                    **auth,
                ),
            ),
            logger,
        )

    if restaurant_id and menu_id and http_method == "PATCH" and _is_admin_menu_detail(event):
        return with_backend(
            "restaurants_service",
            "restaurants_admin_menu_patch",
            lambda: (
                200,
                CognitoRestaurantService.patch_admin_menu(
                    restaurant_id=restaurant_id,
                    menu_id=menu_id,
                    body=json_body(event),
                    **auth,
                ),
            ),
            logger,
        )

    if restaurant_id and menu_id and http_method == "DELETE" and _is_admin_menu_detail(event):
        def operation():
            CognitoRestaurantService.delete_admin_menu(
                restaurant_id=restaurant_id,
                menu_id=menu_id,
                **auth,
            )
            return 204, None

        return with_backend("restaurants_service", "restaurants_admin_menu_delete", operation, logger)

    if restaurant_id and menu_id and http_method == "GET" and _is_menu_categories_collection(event):
        return with_backend(
            "restaurants_service",
            "restaurants_menu_categories_list",
            lambda: (
                200,
                CognitoRestaurantService.list_menu_categories(
                    restaurant_id=restaurant_id,
                    menu_id=menu_id,
                    **auth,
                ),
            ),
            logger,
        )

    if restaurant_id and menu_id and http_method == "POST" and _is_menu_categories_collection(event):
        return with_backend(
            "restaurants_service",
            "restaurants_menu_categories_post",
            lambda: (
                201,
                CognitoRestaurantService.create_menu_category(
                    restaurant_id=restaurant_id,
                    menu_id=menu_id,
                    body=json_body(event),
                    **auth,
                ),
            ),
            logger,
        )

    category_id = _category_id(event)
    if (
        restaurant_id
        and menu_id
        and category_id
        and http_method == "GET"
        and _is_menu_category_detail(event)
    ):
        return with_backend(
            "restaurants_service",
            "restaurants_menu_category_get",
            lambda: (
                200,
                CognitoRestaurantService.get_menu_category(
                    restaurant_id=restaurant_id,
                    menu_id=menu_id,
                    category_id=category_id,
                    **auth,
                ),
            ),
            logger,
        )

    if (
        restaurant_id
        and menu_id
        and category_id
        and http_method == "PUT"
        and _is_menu_category_detail(event)
    ):
        return with_backend(
            "restaurants_service",
            "restaurants_menu_category_put",
            lambda: (
                200,
                CognitoRestaurantService.update_menu_category(
                    restaurant_id=restaurant_id,
                    menu_id=menu_id,
                    category_id=category_id,
                    body=json_body(event),
                    **auth,
                ),
            ),
            logger,
        )

    if (
        restaurant_id
        and menu_id
        and category_id
        and http_method == "DELETE"
        and _is_menu_category_detail(event)
    ):
        def operation():
            CognitoRestaurantService.delete_menu_category(
                restaurant_id=restaurant_id,
                menu_id=menu_id,
                category_id=category_id,
                **auth,
            )
            return 204, None

        return with_backend("restaurants_service", "restaurants_menu_category_delete", operation, logger)

    if restaurant_id and menu_id and category_id and http_method == "GET" and _is_menu_items_collection(event):
        return with_backend(
            "restaurants_service",
            "restaurants_menu_items_list",
            lambda: (
                200,
                CognitoRestaurantService.list_menu_items(
                    restaurant_id=restaurant_id,
                    menu_id=menu_id,
                    category_id=category_id,
                    **auth,
                ),
            ),
            logger,
        )

    if restaurant_id and menu_id and category_id and http_method == "POST" and _is_menu_items_collection(event):
        return with_backend(
            "restaurants_service",
            "restaurants_menu_items_post",
            lambda: (
                201,
                CognitoRestaurantService.create_menu_item(
                    restaurant_id=restaurant_id,
                    menu_id=menu_id,
                    category_id=category_id,
                    body=json_body(event),
                    **auth,
                ),
            ),
            logger,
        )

    item_id = _item_id(event)
    if (
        restaurant_id
        and menu_id
        and category_id
        and item_id
        and http_method == "GET"
        and _is_menu_item_detail(event)
    ):
        return with_backend(
            "restaurants_service",
            "restaurants_menu_item_get",
            lambda: (
                200,
                CognitoRestaurantService.get_menu_item(
                    restaurant_id=restaurant_id,
                    menu_id=menu_id,
                    category_id=category_id,
                    item_id=item_id,
                    **auth,
                ),
            ),
            logger,
        )

    if (
        restaurant_id
        and menu_id
        and category_id
        and item_id
        and http_method == "PUT"
        and _is_menu_item_detail(event)
    ):
        return with_backend(
            "restaurants_service",
            "restaurants_menu_item_put",
            lambda: (
                200,
                CognitoRestaurantService.update_menu_item(
                    restaurant_id=restaurant_id,
                    menu_id=menu_id,
                    category_id=category_id,
                    item_id=item_id,
                    body=json_body(event),
                    **auth,
                ),
            ),
            logger,
        )

    if (
        restaurant_id
        and menu_id
        and category_id
        and item_id
        and http_method == "DELETE"
        and _is_menu_item_detail(event)
    ):
        def operation():
            CognitoRestaurantService.delete_menu_item(
                restaurant_id=restaurant_id,
                menu_id=menu_id,
                category_id=category_id,
                item_id=item_id,
                **auth,
            )
            return 204, None

        return with_backend("restaurants_service", "restaurants_menu_item_delete", operation, logger)

    if restaurant_id and http_method == "GET" and path == f"/restaurants/{restaurant_id}/tables":
        return with_backend(
            "restaurants_service",
            "restaurants_tables_list",
            lambda: (200, CognitoRestaurantService.list_tables(restaurant_id=restaurant_id, **auth)),
            logger,
        )

    if restaurant_id and http_method == "POST" and path == f"/restaurants/{restaurant_id}/tables":
        return with_backend(
            "restaurants_service",
            "restaurants_tables_post",
            lambda: (
                201,
                CognitoRestaurantService.create_table(
                    restaurant_id=restaurant_id,
                    body=json_body(event),
                    **auth,
                ),
            ),
            logger,
        )

    table_id = _table_id(event)
    if restaurant_id and table_id and http_method == "GET" and path.endswith(f"/tables/{table_id}"):
        return with_backend(
            "restaurants_service",
            "restaurants_table_get",
            lambda: (
                200,
                CognitoRestaurantService.get_table(
                    restaurant_id=restaurant_id,
                    table_id=table_id,
                    **auth,
                ),
            ),
            logger,
        )

    if restaurant_id and table_id and http_method == "PUT" and path.endswith(f"/tables/{table_id}"):
        return with_backend(
            "restaurants_service",
            "restaurants_table_put",
            lambda: (
                200,
                CognitoRestaurantService.update_table(
                    restaurant_id=restaurant_id,
                    table_id=table_id,
                    body=json_body(event),
                    **auth,
                ),
            ),
            logger,
        )

    if restaurant_id and table_id and http_method == "DELETE" and path.endswith(f"/tables/{table_id}"):
        def operation():
            CognitoRestaurantService.delete_table(
                restaurant_id=restaurant_id,
                table_id=table_id,
                **auth,
            )
            return 204, None

        return with_backend("restaurants_service", "restaurants_table_delete", operation, logger)

    if restaurant_id and http_method == "GET" and path == f"/restaurants/{restaurant_id}/business-hours":
        return with_backend(
            "restaurants_service",
            "restaurants_business_hours_get",
            lambda: (200, CognitoRestaurantService.get_business_hours(restaurant_id=restaurant_id, **auth)),
            logger,
        )

    if restaurant_id and http_method == "PUT" and path == f"/restaurants/{restaurant_id}/business-hours":
        return with_backend(
            "restaurants_service",
            "restaurants_business_hours_put",
            lambda: (
                200,
                CognitoRestaurantService.update_business_hours(
                    restaurant_id=restaurant_id,
                    body=json_body(event),
                    **auth,
                ),
            ),
            logger,
        )

    query = query_params(event)
    if restaurant_id and http_method == "GET" and path == f"/restaurants/{restaurant_id}/availability":
        return with_backend(
            "restaurants_service",
            "restaurants_availability",
            lambda: (
                200,
                CognitoRestaurantService.get_availability(
                    restaurant_id=restaurant_id,
                    on_date=query.get("date"),
                    party_size=query.get("partySize"),
                ),
            ),
            logger,
        )

    if restaurant_id and http_method == "GET" and path == f"/restaurants/{restaurant_id}/public-availability":
        return with_backend(
            "restaurants_service",
            "restaurants_public_availability",
            lambda: (
                200,
                CognitoRestaurantService.get_availability(
                    restaurant_id=restaurant_id,
                    on_date=query.get("date"),
                    party_size=query.get("partySize"),
                ),
            ),
            logger,
        )

    return route_not_found()
