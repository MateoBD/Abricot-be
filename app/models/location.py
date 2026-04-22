from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.utils.uuid7 import new_uuid7


class CountryModel(db.Model):
    __tablename__ = "countries"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=new_uuid7
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    iso_code: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)


class ProvinceModel(db.Model):
    __tablename__ = "provinces"
    __table_args__ = (UniqueConstraint("country_id", "name", name="uq_province_country_name"),)

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=new_uuid7
    )
    country_id: Mapped[UUID] = mapped_column(
        ForeignKey("countries.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class CityModel(db.Model):
    __tablename__ = "cities"
    __table_args__ = (UniqueConstraint("province_id", "name", name="uq_city_province_name"),)

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=new_uuid7
    )
    province_id: Mapped[UUID] = mapped_column(
        ForeignKey("provinces.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class NeighbourhoodModel(db.Model):
    __tablename__ = "neighbourhoods"
    __table_args__ = (UniqueConstraint("city_id", "name", name="uq_neighbourhood_city_name"),)

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=new_uuid7
    )
    city_id: Mapped[UUID] = mapped_column(
        ForeignKey("cities.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
