"""Multi-range business hours: replace single open/close per day with N ranges per day.

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-05-13T12:00:00

Removes the unique constraint (restaurant_id, day_of_week), drops is_closed, makes
opens_at/closes_at NOT NULL, and adds sort_order so multiple time ranges per day are
stored as separate rows ordered by sort_order.

Backward incompatible: closed days (is_closed=True rows) are deleted — closed days are
now represented by the absence of rows for that day.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b3c4d5e6f7a8"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Delete rows that represent closed days or have incomplete times —
    #    in the new model, closed = no rows; open = one or more range rows.
    op.execute(
        "DELETE FROM business_hours WHERE is_closed = true "
        "OR opens_at IS NULL OR closes_at IS NULL"
    )

    # 2. Drop the per-(restaurant, day) unique constraint so multiple ranges fit.
    op.drop_constraint(
        "uq_business_hours_restaurant_day", "business_hours", type_="unique"
    )

    # 3. Make opens_at / closes_at non-nullable (no null rows remain after step 1).
    op.alter_column("business_hours", "opens_at", nullable=False)
    op.alter_column("business_hours", "closes_at", nullable=False)

    # 4. Add sort_order to preserve deterministic ordering within a day.
    op.add_column(
        "business_hours",
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    # 5. Drop the now-redundant is_closed column.
    op.drop_column("business_hours", "is_closed")


def downgrade() -> None:
    # Re-add is_closed (default false; existing rows were open by definition).
    op.add_column(
        "business_hours",
        sa.Column(
            "is_closed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # Remove sort_order.
    op.drop_column("business_hours", "sort_order")

    # Make opens_at / closes_at nullable again.
    op.alter_column("business_hours", "opens_at", nullable=True)
    op.alter_column("business_hours", "closes_at", nullable=True)

    # Keep only the first range (sort_order=0) per (restaurant_id, day_of_week) so the
    # unique constraint can be restored without conflicts.
    op.execute(
        """
        DELETE FROM business_hours
        WHERE id NOT IN (
            SELECT DISTINCT ON (restaurant_id, day_of_week) id
            FROM business_hours
            ORDER BY restaurant_id, day_of_week, opens_at
        )
        """
    )

    # Re-add the single-range unique constraint.
    op.create_unique_constraint(
        "uq_business_hours_restaurant_day",
        "business_hours",
        ["restaurant_id", "day_of_week"],
    )
