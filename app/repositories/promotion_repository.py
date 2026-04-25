from datetime import date
from uuid import UUID

from sqlalchemy import delete, select

from app.extensions import db
from app.models.promotion import PromotionModel
from app.models.promotion_item import PromotionItemModel


class PromotionRepository:
    @staticmethod
    def get_active(restaurant_id: UUID) -> list[PromotionModel]:
        today = date.today()
        return list(
            db.session.execute(
                select(PromotionModel)
                .where(
                    PromotionModel.restaurant_id == restaurant_id,
                    PromotionModel.is_active.is_(True),
                    PromotionModel.start_date <= today,
                    PromotionModel.end_date >= today,
                )
                .order_by(PromotionModel.start_date.desc())
            ).scalars()
        )

    @staticmethod
    def get_all(restaurant_id: UUID) -> list[PromotionModel]:
        return list(
            db.session.execute(
                select(PromotionModel)
                .where(PromotionModel.restaurant_id == restaurant_id)
                .order_by(PromotionModel.created_at.desc())
            ).scalars()
        )

    @staticmethod
    def get_global_feed() -> list[PromotionModel]:
        today = date.today()
        return list(
            db.session.execute(
                select(PromotionModel)
                .where(
                    PromotionModel.is_active.is_(True),
                    PromotionModel.start_date <= today,
                    PromotionModel.end_date >= today,
                )
                .order_by(PromotionModel.created_at.desc())
            ).scalars()
        )

    @staticmethod
    def get_by_id(restaurant_id: UUID, promo_id: UUID) -> PromotionModel | None:
        row = db.session.get(PromotionModel, promo_id)
        if row is None or row.restaurant_id != restaurant_id:
            return None
        return row

    @staticmethod
    def create(promo: PromotionModel) -> PromotionModel:
        db.session.add(promo)
        db.session.commit()
        return promo

    @staticmethod
    def save(promo: PromotionModel) -> PromotionModel:
        db.session.add(promo)
        db.session.commit()
        return promo

    @staticmethod
    def delete(promo: PromotionModel) -> None:
        db.session.execute(
            delete(PromotionItemModel).where(
                PromotionItemModel.promotion_id == promo.id
            )
        )
        db.session.delete(promo)
        db.session.commit()
