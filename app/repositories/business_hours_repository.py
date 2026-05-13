from uuid import UUID

from sqlalchemy import and_, delete, select

from app.extensions import db
from app.models.business_hours import BusinessHoursModel


class BusinessHoursRepository:
    @staticmethod
    def get_all(restaurant_id: UUID) -> list[BusinessHoursModel]:
        """Return all range rows for a restaurant, ordered by day then sort_order."""
        return list(
            db.session.execute(
                select(BusinessHoursModel)
                .where(BusinessHoursModel.restaurant_id == restaurant_id)
                .order_by(BusinessHoursModel.day_of_week, BusinessHoursModel.sort_order)
            ).scalars()
        )

    @staticmethod
    def get_for_date(restaurant_id: UUID, day_of_week: int) -> list[BusinessHoursModel]:
        """Return all range rows for a specific day, ordered by sort_order."""
        return list(
            db.session.execute(
                select(BusinessHoursModel)
                .where(
                    and_(
                        BusinessHoursModel.restaurant_id == restaurant_id,
                        BusinessHoursModel.day_of_week == day_of_week,
                    )
                )
                .order_by(BusinessHoursModel.sort_order)
            ).scalars()
        )

    @staticmethod
    def replace_day(
        restaurant_id: UUID,
        day_of_week: int,
        ranges: list[dict],
    ) -> list[BusinessHoursModel]:
        """Atomically replace all ranges for a day.

        Each dict in `ranges` must have `opens_at` (time) and `closes_at` (time).
        Pass an empty list to mark the day as closed.
        Does NOT commit — caller is responsible for the transaction boundary.
        """
        db.session.execute(
            delete(BusinessHoursModel).where(
                and_(
                    BusinessHoursModel.restaurant_id == restaurant_id,
                    BusinessHoursModel.day_of_week == day_of_week,
                )
            )
        )
        out: list[BusinessHoursModel] = []
        for i, r in enumerate(ranges):
            row = BusinessHoursModel(
                restaurant_id=restaurant_id,
                day_of_week=day_of_week,
                opens_at=r["opens_at"],
                closes_at=r["closes_at"],
                sort_order=i,
            )
            db.session.add(row)
            out.append(row)
        return out
