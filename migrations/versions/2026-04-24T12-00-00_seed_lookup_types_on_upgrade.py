"""seed lookup rows for price ranges and cuisine types

Revision ID: d4b2e7f1a9c3
Revises: c3f1a9e2b4d8
Create Date: 2026-04-24 12:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from uuid6 import uuid7


revision = "d4b2e7f1a9c3"
down_revision = "c3f1a9e2b4d8"
branch_labels = None
depends_on = None


PRICE_RANGE_ROWS = [
    ("ECONOMICO", "$", "Menos de $5.000 por persona", 1),
    ("MODERADO", "$$", "$5.000 - $15.000 por persona", 2),
    ("ELEGANTE", "$$$", "$15.000 - $40.000 por persona", 3),
    ("EXCLUSIVO", "$$$$", "Mas de $40.000 por persona", 4),
]

CUISINE_TYPE_ROWS = [
    ("ARGENTINA", "Parrilla y Criolla"),
    ("ITALIANA", "Pasta y Pizza"),
    ("JAPONESA", "Sushi y Ramen"),
    ("MEDITERRANEA", "Mediterranea"),
    ("MEXICANA", "Mexicana"),
    ("PERUANA", "Peruana"),
    ("AMERICANA", "Americana"),
    ("CHINA", "China"),
    ("FRANCESA", "Francesa"),
    ("CAFE_BAR", "Cafe y Bar"),
    ("VEGANA_VEGETARIANA", "Vegana y Vegetariana"),
    ("MARISCOS", "Mariscos"),
    ("FUSION", "Fusion"),
    ("OTRA", "Otra"),
]


def _price_ranges_table():
    return sa.table(
        "price_ranges",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("slug", sa.String(length=20)),
        sa.column("label", sa.String(length=10)),
        sa.column("description", sa.String(length=200)),
        sa.column("sort_order", sa.Integer()),
    )


def _cuisine_types_table():
    return sa.table(
        "cuisine_types",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("slug", sa.String(length=30)),
        sa.column("label", sa.String(length=100)),
    )


def _upsert_price_ranges() -> None:
    conn = op.get_bind()
    table = _price_ranges_table()

    existing_slugs = set(conn.execute(sa.select(table.c.slug)).scalars().all())
    rows_to_insert = []
    for slug, label, description, sort_order in PRICE_RANGE_ROWS:
        if slug not in existing_slugs:
            rows_to_insert.append(
                {
                    "id": uuid7(),
                    "slug": slug,
                    "label": label,
                    "description": description,
                    "sort_order": sort_order,
                }
            )

    if rows_to_insert:
        op.bulk_insert(table, rows_to_insert)

    for slug, label, description, sort_order in PRICE_RANGE_ROWS:
        op.execute(
            sa.update(table)
            .where(table.c.slug == slug)
            .values(
                label=label,
                description=description,
                sort_order=sort_order,
            )
        )


def _upsert_cuisine_types() -> None:
    conn = op.get_bind()
    table = _cuisine_types_table()

    existing_slugs = set(conn.execute(sa.select(table.c.slug)).scalars().all())
    rows_to_insert = []
    for slug, label in CUISINE_TYPE_ROWS:
        if slug not in existing_slugs:
            rows_to_insert.append(
                {
                    "id": uuid7(),
                    "slug": slug,
                    "label": label,
                }
            )

    if rows_to_insert:
        op.bulk_insert(table, rows_to_insert)

    for slug, label in CUISINE_TYPE_ROWS:
        op.execute(
            sa.update(table)
            .where(table.c.slug == slug)
            .values(label=label)
        )


def upgrade() -> None:
    _upsert_price_ranges()
    _upsert_cuisine_types()


def downgrade() -> None:
    # Keep seeded lookup values to avoid breaking FK references on downgrade.
    pass
