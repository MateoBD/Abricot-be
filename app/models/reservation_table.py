from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.utils.uuid7 import new_uuid7


class ReservationTableModel(db.Model):
    __tablename__ = "reservation_tables"
    __table_args__ = (
        UniqueConstraint(
            "reservation_id",
            "table_id",
            name="uq_reservation_table_pair",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=new_uuid7
    )
    reservation_id: Mapped[UUID] = mapped_column(
        ForeignKey("reservations.id"), nullable=False, index=True
    )
    table_id: Mapped[UUID] = mapped_column(ForeignKey("tables.id"), nullable=False, index=True)
