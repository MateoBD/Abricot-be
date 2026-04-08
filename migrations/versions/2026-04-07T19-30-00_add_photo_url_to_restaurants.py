"""add_photo_url_to_restaurants

Revision ID: 31bf5ef8e67b
Revises: 20ae4de7d56a
Create Date: 2026-04-07 19:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "31bf5ef8e67b"
down_revision = "20ae4de7d56a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "restaurants",
        sa.Column("photo_url", sa.String(length=500), nullable=True),
    )


def downgrade():
    op.drop_column("restaurants", "photo_url")
