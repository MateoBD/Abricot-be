"""add analytics snapshots table

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-06-14 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analytics_snapshots",
        sa.Column("restaurant_id", sa.Uuid(), nullable=False),
        sa.Column("period_date", sa.Date(), nullable=False),
        sa.Column("orders_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "reservations_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "revenue", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("restaurant_id", "period_date"),
    )


def downgrade() -> None:
    op.drop_table("analytics_snapshots")
