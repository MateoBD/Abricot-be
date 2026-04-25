from uuid import UUID

from sqlalchemy import func, select

from app.extensions import db
from app.models.table import TableModel


class TableRepository:
    @staticmethod
    def get_all(restaurant_id: UUID) -> list[TableModel]:
        return list(
            db.session.execute(
                select(TableModel)
                .where(TableModel.restaurant_id == restaurant_id)
                .order_by(TableModel.number)
            ).scalars()
        )

    @staticmethod
    def get_by_id(restaurant_id: UUID, table_id: UUID) -> TableModel | None:
        row = db.session.get(TableModel, table_id)
        if row is None or row.restaurant_id != restaurant_id:
            return None
        return row

    @staticmethod
    def get_max_number(restaurant_id: UUID) -> int | None:
        return db.session.scalar(
            select(func.max(TableModel.number)).where(
                TableModel.restaurant_id == restaurant_id
            )
        )

    @staticmethod
    def bulk_insert(tables: list[TableModel]) -> list[TableModel]:
        for t in tables:
            db.session.add(t)
        db.session.commit()
        return tables

    @staticmethod
    def save(table: TableModel) -> TableModel:
        db.session.add(table)
        db.session.commit()
        return table

    @staticmethod
    def delete(table: TableModel) -> None:
        db.session.delete(table)
        db.session.commit()

    @staticmethod
    def get_active(restaurant_id: UUID) -> list[TableModel]:
        return list(
            db.session.execute(
                select(TableModel)
                .where(
                    TableModel.restaurant_id == restaurant_id,
                    TableModel.is_active.is_(True),
                )
                .order_by(TableModel.number)
            ).scalars()
        )

    @staticmethod
    def get_active_for_update(restaurant_id: UUID) -> list[TableModel]:
        return list(
            db.session.execute(
                select(TableModel)
                .where(
                    TableModel.restaurant_id == restaurant_id,
                    TableModel.is_active.is_(True),
                )
                .order_by(TableModel.number)
                .with_for_update()
            ).scalars()
        )
