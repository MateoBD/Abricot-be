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
    def bulk_reorder(ordered_ids: list[UUID]) -> None:
        for i, cid in enumerate(ordered_ids):
            row = db.session.get(MenuCategoryModel, cid)
            if row is not None:
                row.display_order = i
        db.session.commit()
