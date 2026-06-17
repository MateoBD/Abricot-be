"""add order item snapshot fields (name + promo pricing)

Snapshots the dish name and discount onto each order line so the order is an
immutable record of what was bought and charged:
 - item_name: dish name at order time (survives rename/delete of the menu item)
 - base_unit_price: pre-discount price
 - applied_promotion_id: promo that won (no FK -- must outlive the promotion)
unit_price now holds the EFFECTIVE (discounted) price.

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-06-15 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e6f7a8b9c0d1"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("order_items", sa.Column("item_name", sa.String(length=150), nullable=True))
    op.add_column("order_items", sa.Column("base_unit_price", sa.Numeric(10, 2), nullable=True))
    op.add_column(
        "order_items",
        sa.Column("applied_promotion_id", sa.Uuid(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("order_items", "applied_promotion_id")
    op.drop_column("order_items", "base_unit_price")
    op.drop_column("order_items", "item_name")
