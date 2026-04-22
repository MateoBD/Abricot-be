from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from app.extensions import db
from app.models.menu import MenuModel
from app.models.menu_category import MenuCategoryModel
from app.models.menu_item import MenuItemModel


class MenuItemRepository:
    @staticmethod
    def get_all(category_id: UUID) -> list[MenuItemModel]:
        return list(
            db.session.execute(
                select(MenuItemModel)
                .where(MenuItemModel.category_id == category_id)
                .order_by(MenuItemModel.name)
            ).scalars()
        )

    @staticmethod
    def get_by_id(item_id: UUID) -> MenuItemModel | None:
        return db.session.get(MenuItemModel, item_id)

    @staticmethod
    def validate_items_for_restaurant(
        item_ids: list[UUID], restaurant_id: UUID
    ) -> bool:
        if not item_ids:
            return True
        unique = list(dict.fromkeys(item_ids))
        q = (
            select(func.count())
            .select_from(MenuItemModel)
            .join(MenuCategoryModel, MenuItemModel.category_id == MenuCategoryModel.id)
            .join(MenuModel, MenuCategoryModel.menu_id == MenuModel.id)
            .where(
                MenuModel.restaurant_id == restaurant_id,
                MenuItemModel.id.in_(unique),
            )
        )
        n = int(db.session.scalar(q) or 0)
        return n == len(unique)
