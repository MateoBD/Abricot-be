"""add user sns subscription fields

Revision ID: c4d5e6f7a8b9
Revises: f2a3b4c5d6e7
Create Date: 2026-05-24 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c4d5e6f7a8b9"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("sns_topic_arn", sa.String(length=512), nullable=True))
    op.add_column("users", sa.Column("sns_subscription_arn", sa.String(length=512), nullable=True))
    op.add_column(
        "users",
        sa.Column("sns_subscription_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("sns_subscription_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_users_sns_subscription_status",
        "users",
        ["sns_subscription_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_users_sns_subscription_status", table_name="users")
    op.drop_column("users", "sns_subscription_requested_at")
    op.drop_column("users", "sns_subscription_status")
    op.drop_column("users", "sns_subscription_arn")
    op.drop_column("users", "sns_topic_arn")
