from uuid import UUID

from sqlalchemy import select

from app.extensions import db
from app.models.cuisine_type import CuisineTypeModel
from app.models.location import CityModel, CountryModel, NeighbourhoodModel, ProvinceModel
from app.models.price_range import PriceRangeModel


class LookupRepository:
    @staticmethod
    def get_country_by_id(country_id: UUID) -> CountryModel | None:
        return db.session.get(CountryModel, country_id)

    @staticmethod
    def get_province_by_id(province_id: UUID) -> ProvinceModel | None:
        return db.session.get(ProvinceModel, province_id)

    @staticmethod
    def get_city_by_id(city_id: UUID) -> CityModel | None:
        return db.session.get(CityModel, city_id)

    @staticmethod
    def list_countries() -> list[CountryModel]:
        return list(
            db.session.execute(select(CountryModel).order_by(CountryModel.name)).scalars()
        )

    @staticmethod
    def list_provinces_by_country(country_id: UUID) -> list[ProvinceModel]:
        return list(
            db.session.execute(
                select(ProvinceModel)
                .where(ProvinceModel.country_id == country_id)
                .order_by(ProvinceModel.name)
            ).scalars()
        )

    @staticmethod
    def list_cities_by_province(province_id: UUID) -> list[CityModel]:
        return list(
            db.session.execute(
                select(CityModel)
                .where(CityModel.province_id == province_id)
                .order_by(CityModel.name)
            ).scalars()
        )

    @staticmethod
    def list_neighbourhoods_by_city(city_id: UUID) -> list[NeighbourhoodModel]:
        return list(
            db.session.execute(
                select(NeighbourhoodModel)
                .where(NeighbourhoodModel.city_id == city_id)
                .order_by(NeighbourhoodModel.name)
            ).scalars()
        )

    @staticmethod
    def list_price_ranges() -> list[PriceRangeModel]:
        return list(
            db.session.execute(
                select(PriceRangeModel).order_by(PriceRangeModel.sort_order)
            ).scalars()
        )

    @staticmethod
    def list_cuisine_types() -> list[CuisineTypeModel]:
        return list(
            db.session.execute(select(CuisineTypeModel).order_by(CuisineTypeModel.label)).scalars()
        )

    @staticmethod
    def get_or_create_city(name: str, province_id: UUID) -> CityModel:
        name = name.strip()
        existing = db.session.execute(
            select(CityModel).where(
                CityModel.province_id == province_id,
                CityModel.name == name,
            )
        ).scalar_one_or_none()
        if existing:
            return existing
        city = CityModel(province_id=province_id, name=name)
        db.session.add(city)
        db.session.commit()
        return city

    @staticmethod
    def get_or_create_neighbourhood(name: str, city_id: UUID) -> NeighbourhoodModel:
        name = name.strip()
        existing = db.session.execute(
            select(NeighbourhoodModel).where(
                NeighbourhoodModel.city_id == city_id,
                NeighbourhoodModel.name == name,
            )
        ).scalar_one_or_none()
        if existing:
            return existing
        n = NeighbourhoodModel(city_id=city_id, name=name)
        db.session.add(n)
        db.session.commit()
        return n
