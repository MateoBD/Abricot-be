from datetime import date, time
from uuid import UUID

from sqlalchemy import func, select

from app.extensions import db
from app.models.enums import ReservationStatus
from app.models.reservation import ReservationModel
from app.models.reservation_table import ReservationTableModel


class ReservationRepository:
    @staticmethod
    def create(reservation: ReservationModel) -> ReservationModel:
        db.session.add(reservation)
        db.session.commit()
        return reservation

    @staticmethod
    def get_by_id(reservation_id: UUID) -> ReservationModel | None:
        return db.session.get(ReservationModel, reservation_id)

    @staticmethod
    def get_by_code(code: str) -> ReservationModel | None:
        return db.session.execute(
            select(ReservationModel).where(ReservationModel.confirmation_code == code)
        ).scalar_one_or_none()

    @staticmethod
    def list_for_user(user_id: UUID, page: int, per_page: int) -> tuple[list[ReservationModel], int]:
        stmt = select(ReservationModel).where(ReservationModel.user_id == user_id)
        count_q = select(func.count()).select_from(ReservationModel).where(
            ReservationModel.user_id == user_id
        )
        total = int(db.session.scalar(count_q) or 0)

        page = max(page, 1)
        per_page = max(min(per_page, 100), 1)
        offset = (page - 1) * per_page

        rows = list(
            db.session.execute(
                stmt.order_by(
                    ReservationModel.date.desc(),
                    ReservationModel.time_slot.desc(),
                )
                .offset(offset)
                .limit(per_page)
            ).scalars()
        )
        return rows, total

    @staticmethod
    def list_for_restaurant(
        restaurant_id: UUID,
        filters: dict | None,
        page: int,
        per_page: int,
    ) -> tuple[list[ReservationModel], int]:
        stmt = select(ReservationModel).where(
            ReservationModel.restaurant_id == restaurant_id
        )
        count_q = select(func.count()).select_from(ReservationModel).where(
            ReservationModel.restaurant_id == restaurant_id
        )
        if filters:
            if filters.get("date_from"):
                stmt = stmt.where(ReservationModel.date >= filters["date_from"])
                count_q = count_q.where(ReservationModel.date >= filters["date_from"])
            if filters.get("date_to"):
                stmt = stmt.where(ReservationModel.date <= filters["date_to"])
                count_q = count_q.where(ReservationModel.date <= filters["date_to"])
            if filters.get("status") is not None:
                stmt = stmt.where(ReservationModel.status == filters["status"])
                count_q = count_q.where(ReservationModel.status == filters["status"])
            if filters.get("source") is not None:
                stmt = stmt.where(ReservationModel.source == filters["source"])
                count_q = count_q.where(ReservationModel.source == filters["source"])
        total = int(db.session.scalar(count_q) or 0)

        page = max(page, 1)
        per_page = max(min(per_page, 100), 1)
        offset = (page - 1) * per_page

        rows = list(
            db.session.execute(
                stmt.order_by(
                    ReservationModel.date.desc(),
                    ReservationModel.time_slot.desc(),
                )
                .offset(offset)
                .limit(per_page)
            ).scalars()
        )
        return rows, total

    @staticmethod
    def get_occupied_table_ids_at(
        restaurant_id: UUID, on_date: date, time_slot: time
    ) -> set[UUID]:
        q = (
            select(ReservationTableModel.table_id)
            .join(
                ReservationModel,
                ReservationTableModel.reservation_id == ReservationModel.id,
            )
            .where(
                ReservationModel.restaurant_id == restaurant_id,
                ReservationModel.date == on_date,
                ReservationModel.time_slot == time_slot,
                ReservationModel.status == ReservationStatus.CONFIRMED,
            )
        )
        return set(db.session.execute(q).scalars())
