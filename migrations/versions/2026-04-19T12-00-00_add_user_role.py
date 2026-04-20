"""add user role column

Revision ID: c8f4a2b91d3e
Revises: 31bf5ef8e67b
Create Date: 2026-04-19 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "c8f4a2b91d3e"
down_revision = "31bf5ef8e67b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=32),
            nullable=False,
            server_default="CUSTOMER",
        ),
    )
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_column("users", "role")
