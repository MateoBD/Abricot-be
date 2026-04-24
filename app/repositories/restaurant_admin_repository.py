from uuid import UUID

from app.extensions import db
from app.models.restaurant_admin import RestaurantAdminModel


class RestaurantAdminRepository:
    @staticmethod
    def is_admin(user_id: UUID, restaurant_id: UUID) -> bool:
        stmt = db.select(RestaurantAdminModel.id).where(
            RestaurantAdminModel.user_id == user_id,
            RestaurantAdminModel.restaurant_id == restaurant_id,
        )
        return db.session.execute(stmt).scalar_one_or_none() is not None

    @staticmethod
    def add(
        user_id: UUID,
        restaurant_id: UUID,
        *,
        auto_commit: bool = True,
    ) -> RestaurantAdminModel:
        relation = RestaurantAdminModel(user_id=user_id, restaurant_id=restaurant_id)
        db.session.add(relation)
        if auto_commit:
            db.session.commit()
        return relation

    @staticmethod
    def add_if_missing(
        user_id: UUID,
        restaurant_id: UUID,
        *,
        auto_commit: bool = True,
    ) -> RestaurantAdminModel:
        existing = db.session.execute(
            db.select(RestaurantAdminModel).where(
                RestaurantAdminModel.user_id == user_id,
                RestaurantAdminModel.restaurant_id == restaurant_id,
            )
        ).scalar_one_or_none()
        if existing:
            return existing
        return RestaurantAdminRepository.add(
            user_id=user_id,
            restaurant_id=restaurant_id,
            auto_commit=auto_commit,
        )

    @staticmethod
    def get_restaurants_for_user(user_id: UUID) -> list[UUID]:
        stmt = db.select(RestaurantAdminModel.restaurant_id).where(
            RestaurantAdminModel.user_id == user_id
        )
        return [row[0] for row in db.session.execute(stmt).all()]

    @staticmethod
    def get_admin_user_ids_for_restaurant(restaurant_id: UUID) -> list[UUID]:
        stmt = db.select(RestaurantAdminModel.user_id).where(
            RestaurantAdminModel.restaurant_id == restaurant_id
        )
        return [row[0] for row in db.session.execute(stmt).all()]

    @staticmethod
    def remove(user_id: UUID, restaurant_id: UUID) -> bool:
        relation = db.session.execute(
            db.select(RestaurantAdminModel).where(
                RestaurantAdminModel.user_id == user_id,
                RestaurantAdminModel.restaurant_id == restaurant_id,
            )
        ).scalar_one_or_none()
        if not relation:
            return False
        db.session.delete(relation)
        db.session.commit()
        return True
