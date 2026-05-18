"""add users cognito_sub

Revision ID: f2a3b4c5d6e7
Revises: b3c4d5e6f7a8
Create Date: 2026-05-18 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f2a3b4c5d6e7"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("cognito_sub", sa.String(length=255), nullable=True))
    op.create_index("ix_users_cognito_sub", "users", ["cognito_sub"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_cognito_sub", table_name="users")
    op.drop_column("users", "cognito_sub")
