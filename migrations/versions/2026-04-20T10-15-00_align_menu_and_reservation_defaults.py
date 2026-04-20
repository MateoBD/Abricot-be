"""align menu and reservation defaults

Revision ID: a91d5f2e7c1b
Revises: f7d329a1b4ce
Create Date: 2026-04-20 10:15:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "a91d5f2e7c1b"
down_revision = "f7d329a1b4ce"
branch_labels = None
depends_on = None


def upgrade():
    # Keep existing rows valid before shrinking the column.
    op.execute("UPDATE reservations SET confirmation_code = LEFT(confirmation_code, 12)")

    op.alter_column(
        "menus",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    op.alter_column(
        "reservations",
        "source",
        existing_type=sa.String(length=16),
        server_default="ONLINE",
        existing_nullable=False,
    )

    op.alter_column(
        "reservations",
        "confirmation_code",
        existing_type=sa.String(length=20),
        type_=sa.String(length=12),
        existing_nullable=False,
    )


def downgrade():
    op.alter_column(
        "reservations",
        "confirmation_code",
        existing_type=sa.String(length=12),
        type_=sa.String(length=20),
        existing_nullable=False,
    )

    op.alter_column(
        "reservations",
        "source",
        existing_type=sa.String(length=16),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "menus",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )
