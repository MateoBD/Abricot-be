from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.restaurant_review import RestaurantReviewModel


class RestaurantReviewRepository:
    @staticmethod
    def get_stats_by_restaurant_ids(
        restaurant_ids: list[UUID],
    ) -> dict[UUID, tuple[float | None, int]]:
        """
        Returns { restaurant_id: (average_score, review_count) }.
        Omitted keys mean zero reviews; average is None in that case (caller merges).
        """
        if not restaurant_ids:
            return {}
        row_tuples = db.session.execute(
            select(
                RestaurantReviewModel.restaurant_id,
                func.avg(RestaurantReviewModel.score * 1.0),
                func.count(RestaurantReviewModel.id),
            )
            .where(RestaurantReviewModel.restaurant_id.in_(restaurant_ids))
            .group_by(RestaurantReviewModel.restaurant_id)
        ).all()
        by_id: dict[UUID, tuple[float | None, int]] = {}
        for rid, avg_val, cnt in row_tuples:
            count = int(cnt)
            if count == 0:
                by_id[rid] = (None, 0)
            else:
                avg = round(float(avg_val or 0.0), 2)
                by_id[rid] = (avg, count)
        return {rid: by_id.get(rid, (None, 0)) for rid in restaurant_ids}

    @staticmethod
    def upsert(
        user_id: UUID,
        restaurant_id: UUID,
        score: int,
    ) -> RestaurantReviewModel:
        """One row per (user_id, restaurant_id). Updates score and updated_at if exists."""
        row = db.session.execute(
            select(RestaurantReviewModel).where(
                RestaurantReviewModel.user_id == user_id,
                RestaurantReviewModel.restaurant_id == restaurant_id,
            )
        ).scalar_one_or_none()
        if row is not None:
            row.score = score
            db.session.commit()
            return row
        r = RestaurantReviewModel(
            user_id=user_id,
            restaurant_id=restaurant_id,
            score=score,
        )
        db.session.add(r)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            row = db.session.execute(
                select(RestaurantReviewModel).where(
                    RestaurantReviewModel.user_id == user_id,
                    RestaurantReviewModel.restaurant_id == restaurant_id,
                )
            ).scalar_one()
            row.score = score
            db.session.commit()
            return row
        return r
