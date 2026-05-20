import json
import logging
from typing import Any
from urllib.parse import parse_qs
from uuid import UUID

from app.exceptions.errors import AppError, NotFoundError, ValidationError
from app.services.lookup_service import LookupService
from app.services.menu_service import MenuService
from app.services.restaurant_service import RestaurantService
from common.flask_db import backend_app_context

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_LOOKUP_TYPES = (
    "country",
    "province",
    "city",
    "neighbourhood",
    "price-range",
    "cuisine-type",
)


def _json_response(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(payload, default=str),
    }


def _route_not_found() -> dict[str, Any]:
    return _json_response(
        404,
        {"message": "Route not found.", "code": "NOT_FOUND", "errors": {}},
    )


def _app_error_response(error: AppError) -> dict[str, Any]:
    return _json_response(
        error.status_code,
        {
            "message": error.public_message,
            "code": error.code,
            "errors": error.payload,
        },
    )


def _database_error_response(error: RuntimeError) -> dict[str, Any]:
    logger.warning("catalog_db_configuration_error type=%s", str(error).split(":", 1)[0])
    return _json_response(
        500,
        {
            "message": "Catalog service database is not configured.",
            "code": "DB_CONFIGURATION_ERROR",
            "errors": {},
        },
    )


def _unexpected_error_response(error: Exception) -> dict[str, Any]:
    logger.exception("catalog_service_failed type=%s", type(error).__name__)
    return _json_response(
        500,
        {
            "message": "Catalog service failed.",
            "code": "INTERNAL_ERROR",
            "errors": {},
        },
    )


def _with_backend(callable_):
    try:
        with backend_app_context():
            return _json_response(200, callable_())
    except AppError as exc:
        return _app_error_response(exc)
    except RuntimeError as exc:
        if str(exc).startswith(("missing_db_env", "invalid_db_target")):
            return _database_error_response(exc)
        return _unexpected_error_response(exc)
    except Exception as exc:
        return _unexpected_error_response(exc)


def _route_path(event: dict[str, Any]) -> str:
    return (
        event.get("rawPath")
        or event.get("path")
        or event.get("requestContext", {}).get("http", {}).get("path")
        or ""
    )


def _method(event: dict[str, Any]) -> str:
    return (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or ""
    ).upper()


def _query_params(event: dict[str, Any]) -> dict[str, str]:
    raw = event.get("queryStringParameters") or {}
    return {key: str(value) for key, value in raw.items() if value is not None}


def _multi_query_params(event: dict[str, Any]) -> dict[str, list[str]]:
    raw_query = event.get("rawQueryString") or ""
    parsed = parse_qs(raw_query, keep_blank_values=False)
    if parsed:
        return {key: [str(item) for item in values] for key, values in parsed.items()}
    return {key: [value] for key, value in _query_params(event).items()}


def _query_values(
    event: dict[str, Any],
    query: dict[str, str],
    *names: str,
) -> list[str]:
    multi = _multi_query_params(event)
    values: list[str] = []

    for name in names:
        values.extend(multi.get(name, []))
        if name in query and query[name] not in values:
            values.append(query[name])

    out: list[str] = []
    for value in values:
        for part in str(value).split(","):
            token = part.strip()
            if token:
                out.append(token)

    return list(dict.fromkeys(out))


def _path_parameters(event: dict[str, Any]) -> dict[str, str]:
    raw = event.get("pathParameters") or {}
    return {key: str(value) for key, value in raw.items() if value is not None}


def _parse_restaurant_path(path: str, path_params: dict[str, str]) -> tuple[str | None, str | None]:
    restaurant_id = path_params.get("restaurantId")
    if restaurant_id:
        parts = path.strip("/").split("/")
        subresource = parts[2] if len(parts) >= 3 else None
        return restaurant_id, subresource

    parts = path.strip("/").split("/")
    if len(parts) < 2 or parts[0] != "restaurants":
        return None, None
    return parts[1] or None, parts[2] if len(parts) >= 3 else None


def _int_query(query: dict[str, str], name: str, default: int) -> int:
    try:
        return int(query.get(name, str(default)))
    except ValueError:
        return default


def _uuid(value: str, field: str) -> UUID:
    try:
        return UUID(str(value))
    except ValueError as exc:
        raise ValidationError("Invalid identifier format.", {field: "Invalid UUID"}) from exc


def _parent_id(query: dict[str, str], lookup_type: str) -> str:
    value = (query.get("parentId") or "").strip()
    if not value:
        raise ValidationError(
            "parentId is required for this lookup type.",
            {"parentId": f"Required when type={lookup_type}"},
        )
    return value


def _handle_list_restaurants(event: dict[str, Any], query: dict[str, str]) -> dict[str, Any]:
    cuisine_type_ids = _query_values(
        event,
        query,
        "cuisineTypeIds",
        "cuisineTypeId",
        "cuisineTypeIds[]",
    )

    return _with_backend(
        lambda: RestaurantService.search(
            name=query.get("name"),
            country_id=query.get("countryId"),
            province_id=query.get("provinceId"),
            city_id=query.get("cityId"),
            neighbourhood_id=query.get("neighbourhoodId"),
            price_range_id=query.get("priceRangeId"),
            cuisine_type_ids=cuisine_type_ids or None,
            sort=query.get("sort", "name") or "name",
            page=_int_query(query, "page", 1),
            per_page=_int_query(query, "perPage", 20),
        )
    )


def _handle_get_restaurant(restaurant_id_raw: str) -> dict[str, Any]:
    return _with_backend(
        lambda: RestaurantService.get_by_id(_uuid(restaurant_id_raw, "restaurantId"))
    )


def _handle_active_menu(restaurant_id_raw: str) -> dict[str, Any]:
    def call_service() -> dict[str, Any]:
        menu = MenuService.get_active_menu(_uuid(restaurant_id_raw, "restaurantId"))
        if menu is None:
            raise NotFoundError("Restaurant has no active menu.")
        return menu

    return _with_backend(call_service)


def _handle_lookups(query: dict[str, str]) -> dict[str, Any]:
    lookup_type = (query.get("type") or "").strip().lower()

    def call_service() -> dict[str, Any]:
        if lookup_type in ("cuisine-type", "cuisine-types"):
            return LookupService.get_all_cuisines()
        if lookup_type in ("price-range", "price-ranges"):
            return LookupService.get_all_price_ranges()
        if lookup_type in ("country", "countries"):
            return LookupService.get_all_countries()
        if lookup_type in ("province", "provinces"):
            return LookupService.get_provinces_by_country(_parent_id(query, "province"))
        if lookup_type in ("city", "cities"):
            return LookupService.get_cities_by_province(_parent_id(query, "city"))
        if lookup_type in ("neighbourhood", "neighbourhoods"):
            return LookupService.get_neighbourhoods_by_city(_parent_id(query, "neighbourhood"))

        raise ValidationError(
            "Invalid lookup type.",
            {"type": "Must be one of: " + ", ".join(_LOOKUP_TYPES)},
        )

    return _with_backend(call_service)


def handler(event, context):
    event = event or {}
    path = _route_path(event)
    method = _method(event)
    query = _query_params(event)
    path_params = _path_parameters(event)

    if method != "GET":
        return _route_not_found()

    if path.rstrip("/") == "/lookups":
        return _handle_lookups(query)

    if path.rstrip("/") == "/restaurants":
        return _handle_list_restaurants(event, query)

    restaurant_id, subresource = _parse_restaurant_path(path, path_params)
    if restaurant_id is not None:
        if subresource == "menus":
            if str(query.get("isActive", "")).lower() != "true":
                return _route_not_found()
            return _handle_active_menu(restaurant_id)
        if subresource is None:
            return _handle_get_restaurant(restaurant_id)
        return _route_not_found()

    return _route_not_found()
