from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, DateTime, Integer, Numeric, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class AnalyticsSnapshotModel(db.Model):
    """Per-restaurant, per-day aggregate of operational activity.

    Rows are recomputed (not incremented) from the operational tables so the
    snapshot is idempotent under SQS redelivery. The composite primary key
    (restaurant_id, period_date) lets the worker UPSERT a single row per day.
    """

    __tablename__ = "analytics_snapshots"

    restaurant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, nullable=False
    )
    period_date: Mapped[date] = mapped_column(Date, primary_key=True, nullable=False)
    orders_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    reservations_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    revenue: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def to_dict(self) -> dict:
        return {
            "restaurantId": str(self.restaurant_id),
            "periodDate": self.period_date.isoformat(),
            "ordersCount": int(self.orders_count or 0),
            "reservationsCount": int(self.reservations_count or 0),
            "revenue": f"{Decimal(self.revenue or 0):.2f}",
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }
