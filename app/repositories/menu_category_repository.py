from uuid import UUID

from sqlalchemy import select

from app.extensions import db
from app.models.menu_category import MenuCategoryModel


class MenuCategoryRepository:
    @staticmethod
    def get_all(menu_id: UUID) -> list[MenuCategoryModel]:
        return list(
            db.session.execute(
                select(MenuCategoryModel)
                .where(MenuCategoryModel.menu_id == menu_id)
                .order_by(MenuCategoryModel.display_order, MenuCategoryModel.name)
            ).scalars()
        )

    @staticmethod
    def get_by_id(menu_id: UUID, category_id: UUID) -> MenuCategoryModel | None:
        row = db.session.get(MenuCategoryModel, category_id)
        if row is None or row.menu_id != menu_id:
            return None
        return row

    @staticmethod
    def get_by_category_id(category_id: UUID) -> MenuCategoryModel | None:
        return db.session.get(MenuCategoryModel, category_id)

    @staticmethod
    def create(menu_id: UUID, name: str, display_order: int = 0) -> MenuCategoryModel:
        cat = MenuCategoryModel(menu_id=menu_id, name=name, display_order=display_order)
        db.session.add(cat)
        db.session.commit()
        return cat

    @staticmethod
    def save(category: MenuCategoryModel) -> MenuCategoryModel:
        db.session.add(category)
        db.session.commit()
        return category

    @staticmethod
    def delete(category: MenuCategoryModel) -> None:
        db.session.delete(category)
        db.session.commit()

    @staticmethod
    def bulk_reorder(ordered_ids: list[UUID]) -> None:
        for i, cid in enumerate(ordered_ids):
            row = db.session.get(MenuCategoryModel, cid)
            if row is not None:
                row.display_order = i
        db.session.commit()
