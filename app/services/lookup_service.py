from uuid import UUID

from app.exceptions.errors import NotFoundError, ValidationError
from app.models.location import CityModel, CountryModel, NeighbourhoodModel, ProvinceModel
from app.models.cuisine_type import CuisineTypeModel
from app.models.price_range import PriceRangeModel
from app.repositories.lookup_repository import LookupRepository
from app.utils.list_envelope import list_envelope


def _parse_uuid(value: str | UUID | None, field: str) -> UUID:
    if value is None or value == "":
        raise ValidationError(f"{field} is required.", {field: "Required"})
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError as error:
        raise ValidationError("Invalid identifier format.", {field: "Invalid UUID"}) from error


def _country_payload(country: CountryModel) -> dict:
    return {
        "id": str(country.id),
        "name": country.name,
        "isoCode": country.iso_code,
    }


def _province_payload(province: ProvinceModel) -> dict:
    return {
        "id": str(province.id),
        "countryId": str(province.country_id),
        "name": province.name,
    }


def _city_payload(city: CityModel) -> dict:
    return {
        "id": str(city.id),
        "provinceId": str(city.province_id),
        "name": city.name,
    }


def _neighbourhood_payload(neighbourhood: NeighbourhoodModel) -> dict:
    return {
        "id": str(neighbourhood.id),
        "cityId": str(neighbourhood.city_id),
        "name": neighbourhood.name,
    }


def _price_range_payload(price_range: PriceRangeModel) -> dict:
    return {
        "id": str(price_range.id),
        "slug": price_range.slug,
        "label": price_range.label,
        "description": price_range.description,
        "sortOrder": price_range.sort_order,
    }


def _cuisine_payload(cuisine: CuisineTypeModel) -> dict:
    return {
        "id": str(cuisine.id),
        "slug": cuisine.slug,
        "label": cuisine.label,
    }


class LookupService:
    @staticmethod
    def get_all_cuisines() -> dict:
        rows = LookupRepository.list_cuisine_types()
        return list_envelope([_cuisine_payload(row) for row in rows])

    @staticmethod
    def get_all_price_ranges() -> dict:
        rows = LookupRepository.list_price_ranges()
        return list_envelope([_price_range_payload(row) for row in rows])

    @staticmethod
    def get_all_countries() -> dict:
        rows = LookupRepository.list_countries()
        return list_envelope([_country_payload(row) for row in rows])

    @staticmethod
    def get_provinces_by_country(country_id: str | UUID) -> dict:
        cid = _parse_uuid(country_id, "countryId")
        if not LookupRepository.get_country_by_id(cid):
            raise NotFoundError(f"Country with id={cid} not found.")

        rows = LookupRepository.list_provinces_by_country(cid)
        return list_envelope([_province_payload(row) for row in rows])

    @staticmethod
    def get_cities_by_province(province_id: str | UUID) -> dict:
        pid = _parse_uuid(province_id, "provinceId")
        if not LookupRepository.get_province_by_id(pid):
            raise NotFoundError(f"Province with id={pid} not found.")

        rows = LookupRepository.list_cities_by_province(pid)
        return list_envelope([_city_payload(row) for row in rows])

    @staticmethod
    def get_neighbourhoods_by_city(city_id: str | UUID) -> dict:
        cid = _parse_uuid(city_id, "cityId")
        if not LookupRepository.get_city_by_id(cid):
            raise NotFoundError(f"City with id={cid} not found.")

        rows = LookupRepository.list_neighbourhoods_by_city(cid)
        return list_envelope([_neighbourhood_payload(row) for row in rows])

    @staticmethod
    def get_or_create_city(city_name: str, province_id: str | UUID) -> dict:
        city_name = city_name.strip()
        if not city_name:
            raise ValidationError("City name is required.", {"cityName": "Required"})

        pid = _parse_uuid(province_id, "provinceId")
        if not LookupRepository.get_province_by_id(pid):
            raise NotFoundError(f"Province with id={pid} not found.")

        city = LookupRepository.get_or_create_city(name=city_name, province_id=pid)
        return _city_payload(city)

    @staticmethod
    def get_or_create_neighbourhood(neighbourhood_name: str, city_id: str | UUID) -> dict:
        neighbourhood_name = neighbourhood_name.strip()
        if not neighbourhood_name:
            raise ValidationError(
                "Neighbourhood name is required.",
                {"neighbourhoodName": "Required"},
            )

        cid = _parse_uuid(city_id, "cityId")
        if not LookupRepository.get_city_by_id(cid):
            raise NotFoundError(f"City with id={cid} not found.")

        neighbourhood = LookupRepository.get_or_create_neighbourhood(
            name=neighbourhood_name,
            city_id=cid,
        )
        return _neighbourhood_payload(neighbourhood)
