from uuid import UUID

from sqlalchemy import delete, select

from app.extensions import db
from app.models.promotion_item import PromotionItemModel


class PromotionItemRepository:
    @staticmethod
    def replace_items(promotion_id: UUID, menu_item_ids: list[UUID]) -> None:
        db.session.execute(
            delete(PromotionItemModel).where(
                PromotionItemModel.promotion_id == promotion_id
            )
        )
        for mid in dict.fromkeys(menu_item_ids):
            db.session.add(
                PromotionItemModel(promotion_id=promotion_id, menu_item_id=mid)
            )
        db.session.commit()

    @staticmethod
    def list_menu_item_ids(promotion_id: UUID) -> list[UUID]:
        return list(
            db.session.execute(
                select(PromotionItemModel.menu_item_id).where(
                    PromotionItemModel.promotion_id == promotion_id
                )
            ).scalars()
        )
