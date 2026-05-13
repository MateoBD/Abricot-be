from uuid import UUID

from sqlalchemy import and_, select

from app.extensions import db
from app.models.business_hours import BusinessHoursModel


class BusinessHoursRepository:
    @staticmethod
    def get_all(restaurant_id: UUID) -> list[BusinessHoursModel]:
        return list(
            db.session.execute(
                select(BusinessHoursModel)
                .where(BusinessHoursModel.restaurant_id == restaurant_id)
                .order_by(BusinessHoursModel.day_of_week)
            ).scalars()
        )

    @staticmethod
    def upsert_bulk(
        restaurant_id: UUID, data: list[dict]
    ) -> list[BusinessHoursModel]:
        """
        Each item: day_of_week, opens_at, closes_at, is_closed (optional keys per row).
        """
        out: list[BusinessHoursModel] = []
        for row in data:
            day = row["day_of_week"]
            existing = db.session.execute(
                select(BusinessHoursModel).where(
                    and_(
                        BusinessHoursModel.restaurant_id == restaurant_id,
                        BusinessHoursModel.day_of_week == day,
                    )
                )
            ).scalar_one_or_none()
            if existing:
                if "opens_at" in row:
                    existing.opens_at = row["opens_at"]
                if "closes_at" in row:
                    existing.closes_at = row["closes_at"]
                if "is_closed" in row:
                    existing.is_closed = row["is_closed"]
                out.append(existing)
            else:
                bh = BusinessHoursModel(
                    restaurant_id=restaurant_id,
                    day_of_week=day,
                    opens_at=row.get("opens_at"),
                    closes_at=row.get("closes_at"),
                    is_closed=row.get("is_closed", False),
                )
                db.session.add(bh)
                out.append(bh)
        db.session.commit()
        return out

    @staticmethod
    def get_for_date(restaurant_id: UUID, day_of_week: int) -> BusinessHoursModel | None:
        return db.session.execute(
            select(BusinessHoursModel).where(
                and_(
                    BusinessHoursModel.restaurant_id == restaurant_id,
                    BusinessHoursModel.day_of_week == day_of_week,
                )
            )
        ).scalar_one_or_none()
