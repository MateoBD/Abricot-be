from datetime import date, time, timedelta
from uuid import UUID

from sqlalchemy import delete, exists, func, select

from app.extensions import db
from app.models.enums import ReservationStatus
from app.models.reservation import ReservationModel
from app.models.reservation_table import ReservationTableModel


class ReservationRepository:
    @staticmethod
    def create(
        reservation: ReservationModel,
        *,
        auto_commit: bool = True,
    ) -> ReservationModel:
        db.session.add(reservation)
        db.session.flush()
        if auto_commit:
            db.session.commit()
        return reservation

    @staticmethod
    def commit() -> None:
        db.session.commit()

    @staticmethod
    def rollback() -> None:
        db.session.rollback()

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
    def update_status(
        reservation: ReservationModel, new_status: ReservationStatus
    ) -> ReservationModel:
        reservation.status = new_status
        db.session.commit()
        return reservation

    @staticmethod
    def cancel_and_release_tables(reservation: ReservationModel) -> ReservationModel:
        reservation.status = ReservationStatus.CANCELLED
        db.session.execute(
            delete(ReservationTableModel).where(
                ReservationTableModel.reservation_id == reservation.id
            )
        )
        db.session.commit()
        return reservation

    @staticmethod
    def mark_no_show_and_release_tables(reservation: ReservationModel) -> ReservationModel:
        reservation.status = ReservationStatus.NO_SHOW
        db.session.execute(
            delete(ReservationTableModel).where(
                ReservationTableModel.reservation_id == reservation.id
            )
        )
        db.session.commit()
        return reservation

    @staticmethod
    def table_has_future_confirmed_reservations(table_id: UUID, from_date: date) -> bool:
        return bool(
            db.session.scalar(
                select(
                    exists(
                        select(ReservationTableModel.id)
                        .join(
                            ReservationModel,
                            ReservationTableModel.reservation_id == ReservationModel.id,
                        )
                        .where(
                            ReservationTableModel.table_id == table_id,
                            ReservationModel.status == ReservationStatus.CONFIRMED,
                            ReservationModel.date >= from_date,
                        )
                    )
                )
            )
        )

    @staticmethod
    def get_occupied_table_ids_at(
        restaurant_id: UUID,
        on_date: date,
        time_slot: time,
        *,
        exclude_reservation_id: UUID | None = None,
    ) -> set[UUID]:
        """
        Get table IDs occupied by confirmed reservations that overlap with the given time interval.
        
        The slot duration is obtained from the restaurant's default_slot_duration_minutes.
        Overlapping is detected by checking if there's any intersection between:
        - [time_slot, time_slot + slot_duration_minutes)
        - [existing_reservation.time_slot, existing_reservation.time_slot + existing_duration)
        
        Two intervals [a1, a2) and [b1, b2) overlap if and only if: a1 < b2 AND b1 < a2
        """
        # Convert time_slot to datetime for interval calculation
        from datetime import datetime
        from app.repositories.restaurant_repository import RestaurantRepository
        
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if restaurant is None:
            return set()
        
        slot_duration_minutes = restaurant.default_slot_duration_minutes
        slot_start = datetime.combine(on_date, time_slot)
        slot_end = slot_start + timedelta(minutes=slot_duration_minutes)
        
        # Get all confirmed reservations for this restaurant and date
        q = (
            select(ReservationTableModel.table_id, ReservationModel.time_slot)
            .join(
                ReservationModel,
                ReservationTableModel.reservation_id == ReservationModel.id,
            )
            .where(
                ReservationModel.restaurant_id == restaurant_id,
                ReservationModel.date == on_date,
                ReservationModel.status == ReservationStatus.CONFIRMED,
            )
        )
        if exclude_reservation_id is not None:
            q = q.where(ReservationModel.id != exclude_reservation_id)
        
        occupied_table_ids = set()
        results = db.session.execute(q).all()
        
        existing_duration_minutes = restaurant.default_slot_duration_minutes
        
        for table_id, existing_time_slot in results:
            existing_start = datetime.combine(on_date, existing_time_slot)
            existing_end = existing_start + timedelta(minutes=existing_duration_minutes)
            
            # Check if intervals overlap: slot_start < existing_end AND existing_start < slot_end
            if slot_start < existing_end and existing_start < slot_end:
                occupied_table_ids.add(table_id)
        
        return occupied_table_ids
