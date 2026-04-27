from uuid import UUID

from sqlalchemy import select, update

from app.extensions import db
from app.models.menu import MenuModel


class MenuRepository:
    @staticmethod
    def get_all(restaurant_id: UUID) -> list[MenuModel]:
        return list(
            db.session.execute(
                select(MenuModel)
                .where(MenuModel.restaurant_id == restaurant_id)
                .order_by(MenuModel.created_at.desc())
            ).scalars()
        )

    @staticmethod
    def get_by_id(restaurant_id: UUID, menu_id: UUID) -> MenuModel | None:
        row = db.session.get(MenuModel, menu_id)
        if row is None or row.restaurant_id != restaurant_id:
            return None
        return row

    @staticmethod
    def get_active(restaurant_id: UUID) -> MenuModel | None:
        return db.session.execute(
            select(MenuModel).where(
                MenuModel.restaurant_id == restaurant_id,
                MenuModel.is_active.is_(True),
            )
        ).scalar_one_or_none()

    @staticmethod
    def create(restaurant_id: UUID, name: str) -> MenuModel:
        menu = MenuModel(restaurant_id=restaurant_id, name=name, is_active=False)
        db.session.add(menu)
        db.session.commit()
        return menu

    @staticmethod
    def activate(restaurant_id: UUID, menu_id: UUID) -> MenuModel | None:
        menu = db.session.get(MenuModel, menu_id)
        if menu is None or menu.restaurant_id != restaurant_id:
            return None
        db.session.execute(
            update(MenuModel)
            .where(MenuModel.restaurant_id == restaurant_id)
            .values(is_active=False)
        )
        menu.is_active = True
        db.session.commit()
        return menu

    @staticmethod
    def deactivate(restaurant_id: UUID, menu_id: UUID) -> MenuModel | None:
        menu = db.session.get(MenuModel, menu_id)
        if menu is None or menu.restaurant_id != restaurant_id:
            return None
        menu.is_active = False
        db.session.commit()
        return menu

    @staticmethod
    def save(menu: MenuModel) -> MenuModel:
        db.session.add(menu)
        db.session.commit()
        return menu

    @staticmethod
    def delete(menu: MenuModel) -> None:
        db.session.delete(menu)
        db.session.commit()

    @staticmethod
    def deactivate_all(restaurant_id: UUID) -> None:
        db.session.execute(
            update(MenuModel)
            .where(MenuModel.restaurant_id == restaurant_id)
            .values(is_active=False)
        )
        db.session.commit()
