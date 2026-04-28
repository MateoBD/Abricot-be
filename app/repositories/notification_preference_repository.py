from uuid import UUID

from sqlalchemy import select

from app.extensions import db
from app.models.notification_preference import NotificationPreferenceModel
from app.models.user import UserModel


class NotificationPreferenceRepository:
    _FIELD_MAP = {
        "receive_promotions": NotificationPreferenceModel.receive_promotions,
        "receive_order_updates": NotificationPreferenceModel.receive_order_updates,
        "receive_reservation_reminders": NotificationPreferenceModel.receive_reservation_reminders,
    }

    @staticmethod
    def get_by_user(user_id: UUID) -> list[NotificationPreferenceModel]:
        return list(
            db.session.execute(
                select(NotificationPreferenceModel).where(
                    NotificationPreferenceModel.user_id == user_id
                )
            ).scalars()
        )

    @staticmethod
    def get_or_create(user_id: UUID, restaurant_id: UUID) -> NotificationPreferenceModel:
        row = db.session.execute(
            select(NotificationPreferenceModel).where(
                NotificationPreferenceModel.user_id == user_id,
                NotificationPreferenceModel.restaurant_id == restaurant_id,
            )
        ).scalar_one_or_none()
        if row:
            return row
        pref = NotificationPreferenceModel(user_id=user_id, restaurant_id=restaurant_id)
        db.session.add(pref)
        db.session.commit()
        return pref

    @staticmethod
    def update(
        user_id: UUID,
        restaurant_id: UUID,
        *,
        receive_promotions: bool | None = None,
        receive_order_updates: bool | None = None,
        receive_reservation_reminders: bool | None = None,
    ) -> NotificationPreferenceModel:
        pref = NotificationPreferenceRepository.get_or_create(user_id, restaurant_id)
        if receive_promotions is not None:
            pref.receive_promotions = receive_promotions
        if receive_order_updates is not None:
            pref.receive_order_updates = receive_order_updates
        if receive_reservation_reminders is not None:
            pref.receive_reservation_reminders = receive_reservation_reminders
        db.session.commit()
        return pref

    @staticmethod
    def get_subscribed_emails(restaurant_id: UUID, field: str) -> list[str]:
        col = NotificationPreferenceRepository._FIELD_MAP.get(field)
        if col is None:
            return []
        rows = db.session.execute(
            select(UserModel.email)
            .join(
                NotificationPreferenceModel,
                NotificationPreferenceModel.user_id == UserModel.id,
            )
            .where(
                NotificationPreferenceModel.restaurant_id == restaurant_id,
                col.is_(True),
                UserModel.email.is_not(None),
            )
        ).all()
        return [r[0] for r in rows if r[0]]
