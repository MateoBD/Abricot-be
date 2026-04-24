"""seed buenos aires neighbourhoods and default menu categories

Revision ID: e8c9b1d4f2a6
Revises: d4b2e7f1a9c3
Create Date: 2026-04-24 12:30:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from uuid6 import uuid7


revision = "e8c9b1d4f2a6"
down_revision = "d4b2e7f1a9c3"
branch_labels = None
depends_on = None


COUNTRY_NAME = "Argentina"
COUNTRY_ISO_CODE = "AR"
PROVINCE_NAME = "Buenos Aires"
CITY_NAME = "Buenos Aires"

BUENOS_AIRES_NEIGHBOURHOODS = [
    "Agronomia",
    "Almagro",
    "Balvanera",
    "Barracas",
    "Belgrano",
    "Boedo",
    "Caballito",
    "Chacarita",
    "Coghlan",
    "Colegiales",
    "Constitucion",
    "Flores",
    "Floresta",
    "La Boca",
    "La Paternal",
    "Liniers",
    "Mataderos",
    "Monte Castro",
    "Monserrat",
    "Nueva Pompeya",
    "Nunez",
    "Palermo",
    "Parque Avellaneda",
    "Parque Chacabuco",
    "Parque Chas",
    "Parque Patricios",
    "Puerto Madero",
    "Recoleta",
    "Retiro",
    "Saavedra",
    "San Cristobal",
    "San Nicolas",
    "San Telmo",
    "Velez Sarsfield",
    "Versalles",
    "Villa Crespo",
    "Villa del Parque",
    "Villa Devoto",
    "Villa General Mitre",
    "Villa Lugano",
    "Villa Luro",
    "Villa Ortuzar",
    "Villa Pueyrredon",
    "Villa Real",
    "Villa Riachuelo",
    "Villa Santa Rita",
    "Villa Soldati",
    "Villa Urquiza",
]

DEFAULT_MENU_CATEGORIES = [
    ("Entradas", 0),
    ("Principales", 1),
    ("Postres", 2),
    ("Bebidas", 3),
]


def _countries_table():
    return sa.table(
        "countries",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("name", sa.String(length=100)),
        sa.column("iso_code", sa.String(length=3)),
    )


def _provinces_table():
    return sa.table(
        "provinces",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("country_id", sa.Uuid(as_uuid=True)),
        sa.column("name", sa.String(length=100)),
    )


def _cities_table():
    return sa.table(
        "cities",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("province_id", sa.Uuid(as_uuid=True)),
        sa.column("name", sa.String(length=100)),
    )


def _neighbourhoods_table():
    return sa.table(
        "neighbourhoods",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("city_id", sa.Uuid(as_uuid=True)),
        sa.column("name", sa.String(length=100)),
    )


def _menus_table():
    return sa.table(
        "menus",
        sa.column("id", sa.Uuid(as_uuid=True)),
    )


def _menu_categories_table():
    return sa.table(
        "menu_categories",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("menu_id", sa.Uuid(as_uuid=True)),
        sa.column("name", sa.String(length=100)),
        sa.column("display_order", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
    )


def _seed_buenos_aires_location() -> None:
    conn = op.get_bind()

    countries = _countries_table()
    provinces = _provinces_table()
    cities = _cities_table()
    neighbourhoods = _neighbourhoods_table()

    country_id = conn.execute(
        sa.select(countries.c.id).where(
            sa.func.lower(countries.c.iso_code) == COUNTRY_ISO_CODE.lower()
        )
    ).scalar_one_or_none()
    if country_id is None:
        country_id = uuid7()
        op.bulk_insert(
            countries,
            [
                {
                    "id": country_id,
                    "name": COUNTRY_NAME,
                    "iso_code": COUNTRY_ISO_CODE,
                }
            ],
        )
    else:
        op.execute(
            sa.update(countries)
            .where(countries.c.id == country_id)
            .values(name=COUNTRY_NAME, iso_code=COUNTRY_ISO_CODE)
        )

    province_id = conn.execute(
        sa.select(provinces.c.id).where(
            provinces.c.country_id == country_id,
            provinces.c.name == PROVINCE_NAME,
        )
    ).scalar_one_or_none()
    if province_id is None:
        province_id = uuid7()
        op.bulk_insert(
            provinces,
            [
                {
                    "id": province_id,
                    "country_id": country_id,
                    "name": PROVINCE_NAME,
                }
            ],
        )

    city_id = conn.execute(
        sa.select(cities.c.id).where(
            cities.c.province_id == province_id,
            cities.c.name == CITY_NAME,
        )
    ).scalar_one_or_none()
    if city_id is None:
        city_id = uuid7()
        op.bulk_insert(
            cities,
            [
                {
                    "id": city_id,
                    "province_id": province_id,
                    "name": CITY_NAME,
                }
            ],
        )

    existing_neighbourhoods = set(
        conn.execute(
            sa.select(neighbourhoods.c.name).where(neighbourhoods.c.city_id == city_id)
        ).scalars()
    )
    rows_to_insert = []
    for name in BUENOS_AIRES_NEIGHBOURHOODS:
        if name not in existing_neighbourhoods:
            rows_to_insert.append(
                {
                    "id": uuid7(),
                    "city_id": city_id,
                    "name": name,
                }
            )

    if rows_to_insert:
        op.bulk_insert(neighbourhoods, rows_to_insert)


def _seed_default_menu_categories() -> None:
    conn = op.get_bind()
    menus = _menus_table()
    categories = _menu_categories_table()

    menu_ids = list(conn.execute(sa.select(menus.c.id)).scalars())
    if not menu_ids:
        return

    rows_to_insert = []
    for menu_id in menu_ids:
        existing_names = set(
            conn.execute(
                sa.select(categories.c.name).where(categories.c.menu_id == menu_id)
            ).scalars()
        )
        for name, display_order in DEFAULT_MENU_CATEGORIES:
            if name not in existing_names:
                rows_to_insert.append(
                    {
                        "id": uuid7(),
                        "menu_id": menu_id,
                        "name": name,
                        "display_order": display_order,
                        "is_active": True,
                    }
                )

    if rows_to_insert:
        op.bulk_insert(categories, rows_to_insert)

    for menu_id in menu_ids:
        for name, display_order in DEFAULT_MENU_CATEGORIES:
            op.execute(
                sa.update(categories)
                .where(
                    categories.c.menu_id == menu_id,
                    categories.c.name == name,
                )
                .values(display_order=display_order, is_active=True)
            )


def upgrade() -> None:
    _seed_buenos_aires_location()
    _seed_default_menu_categories()


def downgrade() -> None:
    # Keep seeded lookup values and category rows to avoid breaking FKs.
    pass
