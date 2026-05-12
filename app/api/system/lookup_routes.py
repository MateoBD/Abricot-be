from uuid import UUID

from flask_restx import Namespace, Resource, reqparse

from app.exceptions.errors import ValidationError
from app.middleware.auth import require_authentication
from app.repositories.lookup_repository import LookupRepository

namespace = Namespace(
    name="Lookups",
    path="/lookups",
    description="Read-only location and metadata lookup resource.",
    decorators=[require_authentication()],
)

_lookup_parser = reqparse.RequestParser()
_lookup_parser.add_argument(
    "type",
    type=str,
    location="args",
    required=True,
    help=(
        "Lookup type: country, province, city, neighbourhood, price-range, "
        "or cuisine-type."
    ),
)
_lookup_parser.add_argument(
    "parentId",
    type=str,
    location="args",
    required=False,
    help="Parent UUID for province, city, and neighbourhood lookups.",
)


def _parse_parent_id(value: str | None, lookup_type: str) -> UUID:
    if not value:
        raise ValidationError(
            "parentId is required for this lookup type.",
            {"parentId": f"Required when type={lookup_type}"},
        )
    try:
        return UUID(value)
    except ValueError as error:
        raise ValidationError(
            "Invalid parentId format.",
            {"parentId": "Must be a valid UUID"},
        ) from error


@namespace.route("")
class LookupCollection(Resource):
    @namespace.expect(_lookup_parser)
    @namespace.response(200, "Lookup values retrieved successfully.")
    @namespace.response(400, "Validation error.")
    def get(self):
        """List lookup values by type."""
        args = _lookup_parser.parse_args()
        lookup_type = str(args.get("type", "")).strip().lower()
        parent_id = args.get("parentId")

        if lookup_type in ("country", "countries"):
            countries = LookupRepository.list_countries()
            return {"data": [{"id": str(c.id), "name": c.name} for c in countries]}, 200

        if lookup_type in ("province", "provinces"):
            country_id = _parse_parent_id(parent_id, "province")
            provinces = LookupRepository.list_provinces_by_country(country_id)
            return {
                "data": [
                    {"id": str(p.id), "name": p.name, "countryId": str(p.country_id)}
                    for p in provinces
                ]
            }, 200

        if lookup_type in ("city", "cities"):
            province_id = _parse_parent_id(parent_id, "city")
            cities = LookupRepository.list_cities_by_province(province_id)
            return {
                "data": [
                    {"id": str(c.id), "name": c.name, "provinceId": str(c.province_id)}
                    for c in cities
                ]
            }, 200

        if lookup_type in ("neighbourhood", "neighbourhoods"):
            city_id = _parse_parent_id(parent_id, "neighbourhood")
            neighbourhoods = LookupRepository.list_neighbourhoods_by_city(city_id)
            return {
                "data": [
                    {"id": str(n.id), "name": n.name, "cityId": str(n.city_id)}
                    for n in neighbourhoods
                ]
            }, 200

        if lookup_type in ("price-range", "price-ranges"):
            price_ranges = LookupRepository.list_price_ranges()
            return {
                "data": [
                    {"id": str(pr.id), "label": pr.label, "description": pr.description}
                    for pr in price_ranges
                ]
            }, 200

        if lookup_type in ("cuisine-type", "cuisine-types"):
            cuisines = LookupRepository.list_cuisine_types()
            return {"data": [{"id": str(c.id), "label": c.label} for c in cuisines]}, 200

        raise ValidationError(
            "Invalid lookup type.",
            {
                "type": (
                    "Must be one of: country, province, city, neighbourhood, "
                    "price-range, cuisine-type"
                )
            },
        )
