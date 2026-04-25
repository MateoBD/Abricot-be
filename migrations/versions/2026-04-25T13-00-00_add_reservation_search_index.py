"""add reservation search index

Revision ID: 6d4e2a7c9b01
Revises: f9a0c1d2e3b4
Create Date: 2026-04-25 13:00:00.000000

"""

from alembic import op


revision = "6d4e2a7c9b01"
down_revision = "f9a0c1d2e3b4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_reservations_restaurant_id_date_status",
        "reservations",
        ["restaurant_id", "date", "status"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_reservations_restaurant_id_date_status",
        table_name="reservations",
    )
