"""Convert integer PK/FK columns to UUID (PostgreSQL).

Revision ID: c3f1a9e2b4d8
Revises: a91d5f2e7c1b
Create Date: 2026-04-21 12:00:00.000000

Destructive: truncates all application data, then converts id / foreign-key columns to UUID.
Application layer must generate UUID v7 on insert (see app.utils.uuid7).

Non-PostgreSQL dialects skip this revision (use a fresh DB from models or PostgreSQL).
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import text
from uuid6 import uuid7

revision = "c3f1a9e2b4d8"
down_revision = "a91d5f2e7c1b"
branch_labels = None
depends_on = None

UUID_TYPE = sa.Uuid(as_uuid=True)


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    op.execute(
        text(
            """
            TRUNCATE TABLE
                promotion_items,
                order_items,
                orders,
                menu_items,
                menu_categories,
                menus,
                reservation_tables,
                reservations,
                business_hours,
                "tables",
                notification_preferences,
                restaurant_cuisines,
                restaurant_admins,
                restaurants,
                users,
                neighbourhoods,
                cities,
                provinces,
                countries,
                price_ranges,
                cuisine_types,
                promotions
            RESTART IDENTITY CASCADE;
            """
        )
    )

    inspector = inspect(conn)
    tables = sorted(inspector.get_table_names())

    fk_specs: list[dict[str, Any]] = []
    for tname in tables:
        for fk in inspector.get_foreign_keys(tname):
            fk_specs.append(
                {
                    "table": tname,
                    "name": fk["name"],
                    "referred_table": fk["referred_table"],
                    "constrained": fk["constrained_columns"],
                    "referred": fk["referred_columns"],
                    "ondelete": fk.get("ondelete"),
                }
            )

    pk_specs: list[tuple[str, str | None]] = []
    for tname in tables:
        pk = inspector.get_pk_constraint(tname)
        if pk.get("name"):
            pk_specs.append((tname, pk["name"]))

    for tname, fk_name in [(f["table"], f["name"]) for f in fk_specs]:
        op.drop_constraint(fk_name, tname, type_="foreignkey")

    for tname, pk_name in pk_specs:
        op.drop_constraint(pk_name, tname, type_="primary")

    int_cols: list[tuple[str, str, bool]] = []
    for tname in tables:
        for col in inspector.get_columns(tname):
            cname = col["name"]
            ctype = col["type"]
            if not (cname == "id" or cname.endswith("_id")):
                continue
            if not isinstance(
                ctype,
                (sa.Integer, sa.SmallInteger, sa.BigInteger),
            ):
                continue
            int_cols.append((tname, cname, col["nullable"]))

    # SERIAL / identity defaults (nextval) cannot be cast to uuid; drop before ALTER TYPE.
    preparer = conn.dialect.identifier_preparer
    for tname, cname, _nullable in int_cols:
        qt = preparer.quote(tname)
        qc = preparer.quote(cname)
        op.execute(text(f"ALTER TABLE {qt} ALTER COLUMN {qc} DROP DEFAULT"))

    for tname, cname, nullable in int_cols:
        op.alter_column(
            tname,
            cname,
            existing_type=sa.Integer(),
            type_=UUID_TYPE,
            existing_nullable=nullable,
            postgresql_using="gen_random_uuid()",
        )

    for tname, pk_name in pk_specs:
        pk_cols = inspector.get_pk_constraint(tname)["constrained_columns"]
        op.create_primary_key(pk_name or f"{tname}_pkey", tname, pk_cols)

    for fk in fk_specs:
        name = fk["name"]
        if not name:
            continue
        opts: dict[str, Any] = {}
        if fk.get("ondelete"):
            opts["ondelete"] = fk["ondelete"]
        op.create_foreign_key(
            name,
            fk["table"],
            fk["referred_table"],
            fk["constrained"],
            fk["referred"],
            **opts,
        )

    _reseed_lookups_postgresql(conn)


def _reseed_lookups_postgresql(_conn: Any) -> None:
    pr_rows = [
        {
            "id": uuid7(),
            "slug": "ECONOMICO",
            "label": "$",
            "description": "Menos de $5.000 por persona",
            "sort_order": 1,
        },
        {
            "id": uuid7(),
            "slug": "MODERADO",
            "label": "$$",
            "description": "$5.000 - $15.000 por persona",
            "sort_order": 2,
        },
        {
            "id": uuid7(),
            "slug": "ELEGANTE",
            "label": "$$$",
            "description": "$15.000 - $40.000 por persona",
            "sort_order": 3,
        },
        {
            "id": uuid7(),
            "slug": "EXCLUSIVO",
            "label": "$$$$",
            "description": "Mas de $40.000 por persona",
            "sort_order": 4,
        },
    ]
    ct_rows = [
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
    cuisine_insert = [
        {"id": uuid7(), "slug": slug, "label": label} for slug, label in ct_rows
    ]

    op.bulk_insert(
        sa.table(
            "price_ranges",
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("slug", sa.String(20)),
            sa.column("label", sa.String(10)),
            sa.column("description", sa.String(200)),
            sa.column("sort_order", sa.Integer()),
        ),
        pr_rows,
    )
    op.bulk_insert(
        sa.table(
            "cuisine_types",
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("slug", sa.String(30)),
            sa.column("label", sa.String(100)),
        ),
        cuisine_insert,
    )


def downgrade() -> None:
    raise NotImplementedError("Integer PK downgrade is not supported.")
