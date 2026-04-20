from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class CountryModel(db.Model):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    iso_code: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)


class ProvinceModel(db.Model):
    __tablename__ = "provinces"
    __table_args__ = (UniqueConstraint("country_id", "name", name="uq_province_country_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class CityModel(db.Model):
    __tablename__ = "cities"
    __table_args__ = (UniqueConstraint("province_id", "name", name="uq_city_province_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    province_id: Mapped[int] = mapped_column(ForeignKey("provinces.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class NeighbourhoodModel(db.Model):
    __tablename__ = "neighbourhoods"
    __table_args__ = (UniqueConstraint("city_id", "name", name="uq_neighbourhood_city_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
