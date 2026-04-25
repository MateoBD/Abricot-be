"""add restaurant_reviews (one user score per restaurant)

Revision ID: f9a0c1d2e3b4
Revises: e8c9b1d4f2a6
Create Date: 2026-04-25 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f9a0c1d2e3b4"
down_revision = "e8c9b1d4f2a6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "restaurant_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("restaurant_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "restaurant_id", name="uq_restaurant_reviews_user_restaurant"
        ),
    )
    op.create_index(
        "ix_restaurant_reviews_restaurant_id", "restaurant_reviews", ["restaurant_id"]
    )
    op.create_index("ix_restaurant_reviews_user_id", "restaurant_reviews", ["user_id"])


def downgrade():
    op.drop_index("ix_restaurant_reviews_user_id", table_name="restaurant_reviews")
    op.drop_index("ix_restaurant_reviews_restaurant_id", table_name="restaurant_reviews")
    op.drop_table("restaurant_reviews")
