from uuid import UUID

from sqlalchemy import delete, select

from app.extensions import db
from app.models.reservation_table import ReservationTableModel
from app.models.table import TableModel


class ReservationTableRepository:
    @staticmethod
    def create_bulk(
        reservation_id: UUID,
        table_ids: list[UUID],
        *,
        auto_commit: bool = True,
    ) -> list[ReservationTableModel]:
        rows: list[ReservationTableModel] = []
        for tid in table_ids:
            row = ReservationTableModel(reservation_id=reservation_id, table_id=tid)
            db.session.add(row)
            rows.append(row)
        if auto_commit:
            db.session.commit()
        return rows

    @staticmethod
    def delete_by_reservation(
        reservation_id: UUID,
        *,
        auto_commit: bool = True,
    ) -> None:
        db.session.execute(
            delete(ReservationTableModel).where(
                ReservationTableModel.reservation_id == reservation_id
            )
        )
        if auto_commit:
            db.session.commit()

    @staticmethod
    def get_tables_for_reservation(reservation_id: UUID) -> list[TableModel]:
        return list(
            db.session.execute(
                select(TableModel)
                .join(
                    ReservationTableModel,
                    ReservationTableModel.table_id == TableModel.id,
                )
                .where(ReservationTableModel.reservation_id == reservation_id)
                .order_by(TableModel.number)
            ).scalars()
        )
