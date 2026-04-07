"""add surname to users

Revision ID: b2c3d4e5f678
Revises: ea1f986a5534
Create Date: 2026-04-07 17:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b2c3d4e5f678"
down_revision = "ea1f986a5534"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("surname", sa.String(length=100), nullable=False, server_default=""),
    )
    op.alter_column("users", "surname", server_default=None)


def downgrade():
    op.drop_column("users", "surname")
