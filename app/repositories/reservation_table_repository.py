from uuid import UUID

from sqlalchemy import delete

from app.extensions import db
from app.models.reservation_table import ReservationTableModel


class ReservationTableRepository:
    @staticmethod
    def create_bulk(reservation_id: UUID, table_ids: list[UUID]) -> list[ReservationTableModel]:
        rows: list[ReservationTableModel] = []
        for tid in table_ids:
            row = ReservationTableModel(reservation_id=reservation_id, table_id=tid)
            db.session.add(row)
            rows.append(row)
        db.session.commit()
        return rows

    @staticmethod
    def delete_by_reservation(reservation_id: UUID) -> None:
        db.session.execute(
            delete(ReservationTableModel).where(
                ReservationTableModel.reservation_id == reservation_id
            )
        )
        db.session.commit()
