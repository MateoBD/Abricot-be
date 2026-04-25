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
    def get_by_ids(item_ids: list[UUID]) -> list[MenuItemModel]:
        if not item_ids:
            return []
        unique = list(dict.fromkeys(item_ids))
        return list(
            db.session.execute(
                select(MenuItemModel).where(MenuItemModel.id.in_(unique))
            ).scalars()
        )

    @staticmethod
    def get_available_for_menu(item_ids: list[UUID], menu_id: UUID) -> list[MenuItemModel]:
        if not item_ids:
            return []
        unique = list(dict.fromkeys(item_ids))
        return list(
            db.session.execute(
                select(MenuItemModel)
                .join(MenuCategoryModel, MenuItemModel.category_id == MenuCategoryModel.id)
                .where(
                    MenuCategoryModel.menu_id == menu_id,
                    MenuCategoryModel.is_active.is_(True),
                    MenuItemModel.is_available.is_(True),
                    MenuItemModel.id.in_(unique),
                )
            ).scalars()
        )

    @staticmethod
    def create(
        category_id: UUID,
        name: str,
        description: str | None,
        price: Decimal,
        is_available: bool = True,
    ) -> MenuItemModel:
        item = MenuItemModel(
            category_id=category_id,
            name=name,
            description=description,
            price=price,
            is_available=is_available,
        )
        db.session.add(item)
        db.session.commit()
        return item

    @staticmethod
    def save(item: MenuItemModel) -> MenuItemModel:
        db.session.add(item)
        db.session.commit()
        return item

    @staticmethod
    def delete(item: MenuItemModel) -> None:
        db.session.delete(item)
        db.session.commit()

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

    @staticmethod
    def validate_items_for_menu(item_ids: list[UUID], menu_id: UUID) -> bool:
        if not item_ids:
            return True
        unique = list(dict.fromkeys(item_ids))
        q = (
            select(func.count())
            .select_from(MenuItemModel)
            .join(MenuCategoryModel, MenuItemModel.category_id == MenuCategoryModel.id)
            .where(
                MenuCategoryModel.menu_id == menu_id,
                MenuItemModel.id.in_(unique),
            )
        )
        n = int(db.session.scalar(q) or 0)
        return n == len(unique)
