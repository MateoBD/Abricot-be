from flask_restx import Namespace, Resource, reqparse
from uuid import UUID

from app.middleware.auth import require_authentication
from app.repositories.lookup_repository import LookupRepository

namespace = Namespace(
    name="Lookup",
    path="/lookup",
    description="Read-only endpoints for location and metadata lookup.",
    decorators=[require_authentication()],
)

_city_parser = reqparse.RequestParser()
_city_parser.add_argument(
    "provinceId",
    type=str,
    location="args",
    required=True,
    help="Province ID (UUID) to filter cities.",
)

_neighbourhood_parser = reqparse.RequestParser()
_neighbourhood_parser.add_argument(
    "cityId",
    type=str,
    location="args",
    required=True,
    help="City ID (UUID) to filter neighbourhoods.",
)

_country_parser = reqparse.RequestParser()
_country_parser.add_argument(
    "countryId",
    type=str,
    location="args",
    required=True,
    help="Country ID (UUID) to filter provinces.",
)


country_model = namespace.model(
    "Country",
    {
        "id": {"type": "string", "description": "Country ID (UUID)"},
        "name": {"type": "string", "description": "Country name"},
    },
)

province_model = namespace.model(
    "Province",
    {
        "id": {"type": "string", "description": "Province ID (UUID)"},
        "name": {"type": "string", "description": "Province name"},
        "countryId": {"type": "string", "description": "Parent country ID (UUID)"},
    },
)

city_model = namespace.model(
    "City",
    {
        "id": {"type": "string", "description": "City ID (UUID)"},
        "name": {"type": "string", "description": "City name"},
        "provinceId": {"type": "string", "description": "Parent province ID (UUID)"},
    },
)

neighbourhood_model = namespace.model(
    "Neighbourhood",
    {
        "id": {"type": "string", "description": "Neighbourhood ID (UUID)"},
        "name": {"type": "string", "description": "Neighbourhood name"},
        "cityId": {"type": "string", "description": "Parent city ID (UUID)"},
    },
)

price_range_model = namespace.model(
    "PriceRange",
    {
        "id": {"type": "string", "description": "Price range ID (UUID)"},
        "label": {"type": "string", "description": "Price range label (e.g. $$)"},
        "description": {"type": "string", "description": "Description"},
    },
)

cuisine_type_model = namespace.model(
    "CuisineType",
    {
        "id": {"type": "string", "description": "Cuisine type ID (UUID)"},
        "label": {"type": "string", "description": "Cuisine name (e.g. Italiana)"},
    },
)


@namespace.route("/countries")
class CountriesList(Resource):
    @namespace.response(200, "Countries retrieved successfully.")
    def get(self):
        """List all countries."""
        countries = LookupRepository.list_countries()
        return {
            "data": [
                {"id": str(c.id), "name": c.name}
                for c in countries
            ]
        }, 200


@namespace.route("/provinces")
class ProvincesList(Resource):
    @namespace.expect(_country_parser)
    @namespace.response(200, "Provinces retrieved successfully.")
    def get(self):
        """List provinces by country ID."""
        args = _country_parser.parse_args()
        country_id = args.get("countryId")
        if not country_id:
            return {"message": "countryId is required", "code": "VALIDATION_ERROR"}, 400
        try:
            country_uuid = UUID(country_id)
        except ValueError:
            return {"message": "Invalid countryId format", "code": "VALIDATION_ERROR"}, 400
        
        provinces = LookupRepository.list_provinces_by_country(country_uuid)
        return {
            "data": [
                {"id": str(p.id), "name": p.name, "countryId": str(p.country_id)}
                for p in provinces
            ]
        }, 200


@namespace.route("/cities")
class CitiesList(Resource):
    @namespace.expect(_city_parser)
    @namespace.response(200, "Cities retrieved successfully.")
    def get(self):
        """List cities by province ID."""
        args = _city_parser.parse_args()
        province_id = args.get("provinceId")
        if not province_id:
            return {"message": "provinceId is required", "code": "VALIDATION_ERROR"}, 400
        try:
            province_uuid = UUID(province_id)
        except ValueError:
            return {"message": "Invalid provinceId format", "code": "VALIDATION_ERROR"}, 400
        
        cities = LookupRepository.list_cities_by_province(province_uuid)
        return {
            "data": [
                {"id": str(c.id), "name": c.name, "provinceId": str(c.province_id)}
                for c in cities
            ]
        }, 200


@namespace.route("/neighbourhoods")
class NeighbourhoodsList(Resource):
    @namespace.expect(_neighbourhood_parser)
    @namespace.response(200, "Neighbourhoods retrieved successfully.")
    def get(self):
        """List neighbourhoods by city ID."""
        args = _neighbourhood_parser.parse_args()
        city_id = args.get("cityId")
        if not city_id:
            return {"message": "cityId is required", "code": "VALIDATION_ERROR"}, 400
        try:
            city_uuid = UUID(city_id)
        except ValueError:
            return {"message": "Invalid cityId format", "code": "VALIDATION_ERROR"}, 400
        
        neighbourhoods = LookupRepository.list_neighbourhoods_by_city(city_uuid)
        return {
            "data": [
                {"id": str(n.id), "name": n.name, "cityId": str(n.city_id)}
                for n in neighbourhoods
            ]
        }, 200


@namespace.route("/price-ranges")
class PriceRangesList(Resource):
    @namespace.response(200, "Price ranges retrieved successfully.")
    def get(self):
        """List all price ranges."""
        price_ranges = LookupRepository.list_price_ranges()
        return {
            "data": [
                {"id": str(pr.id), "label": pr.label, "description": pr.description}
                for pr in price_ranges
            ]
        }, 200


@namespace.route("/cuisine-types")
class CuisineTypesList(Resource):
    @namespace.response(200, "Cuisine types retrieved successfully.")
    def get(self):
        """List all cuisine types."""
        cuisines = LookupRepository.list_cuisine_types()
        return {
            "data": [
                {"id": str(c.id), "label": c.label}
                for c in cuisines
            ]
        }, 200
