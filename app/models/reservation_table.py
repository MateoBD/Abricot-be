from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class ReservationTableModel(db.Model):
    __tablename__ = "reservation_tables"
    __table_args__ = (
        UniqueConstraint(
            "reservation_id",
            "table_id",
            name="uq_reservation_table_pair",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    reservation_id: Mapped[int] = mapped_column(
        ForeignKey("reservations.id"), nullable=False, index=True
    )
    table_id: Mapped[int] = mapped_column(ForeignKey("tables.id"), nullable=False, index=True)
