from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import app.services.notification_service as notification_service_module
from app.extensions import db
from app.models.enums import DiscountType
from app.models.promotion import PromotionModel
from app.services.notification_service import NotificationService


PROMOTION_ID = UUID("00000000-0000-0000-0000-000000000001")
RESTAURANT_ID = UUID("00000000-0000-0000-0000-000000000002")
USER_A_ID = UUID("00000000-0000-0000-0000-0000000000a1")
USER_B_ID = UUID("00000000-0000-0000-0000-0000000000b2")


def _promo(description: str | None = "2x1 en pizzas") -> PromotionModel:
    return PromotionModel(
        id=PROMOTION_ID,
        restaurant_id=RESTAURANT_ID,
        title="Promo de prueba",
        description=description,
        discount_type=DiscountType.PERCENTAGE,
        discount_value=Decimal("20.00"),
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        is_active=True,
        notify_users=True,
        created_at=datetime.now(UTC),
    )


def _patch_promo_lookup(monkeypatch, promo: PromotionModel | None) -> None:
    # publish_promotion_events resolves the promotion via db.session.get(...).
    monkeypatch.setattr(db.session, "get", lambda model, pk: promo)


def _patch_recipients(monkeypatch, user_ids: list[UUID]) -> None:
    monkeypatch.setattr(
        NotificationService,
        "_get_subscribed_user_ids",
        staticmethod(lambda restaurant_id, preference_field: list(user_ids)),
    )


def _capture_events(monkeypatch) -> list[dict]:
    events: list[dict] = []

    def fake_publish(event_type, user_id=None, restaurant_id=None, payload=None):
        events.append(
            {
                "event_type": event_type,
                "user_id": user_id,
                "restaurant_id": restaurant_id,
                "payload": payload,
            }
        )

    monkeypatch.setattr(notification_service_module, "publish_domain_event", fake_publish)
    return events


def test_one_promotion_notify_event_per_recipient(monkeypatch):
    _patch_promo_lookup(monkeypatch, _promo())
    _patch_recipients(monkeypatch, [USER_A_ID, USER_B_ID])
    events = _capture_events(monkeypatch)

    NotificationService.publish_promotion_events(PROMOTION_ID)

    assert len(events) == 2
    assert {e["user_id"] for e in events} == {USER_A_ID, USER_B_ID}

    for event in events:
        assert event["event_type"] == "promotion.notify"
        assert event["restaurant_id"] == RESTAURANT_ID

        payload = event["payload"]
        assert payload["promotionId"] == str(PROMOTION_ID)
        assert payload["restaurantId"] == str(RESTAURANT_ID)
        assert payload["title"] == "Promo de prueba"
        assert payload["description"] == "2x1 en pizzas"


def test_send_promotion_notification_routes_through_event_pipeline(monkeypatch):
    _patch_promo_lookup(monkeypatch, _promo())
    _patch_recipients(monkeypatch, [USER_A_ID])
    events = _capture_events(monkeypatch)

    # Legacy entrypoint must now publish domain events (no MockSES path).
    NotificationService.send_promotion_notification(PROMOTION_ID)

    assert len(events) == 1
    assert events[0]["event_type"] == "promotion.notify"
    assert events[0]["user_id"] == USER_A_ID


def test_missing_description_publishes_empty_string(monkeypatch):
    _patch_promo_lookup(monkeypatch, _promo(description=None))
    _patch_recipients(monkeypatch, [USER_A_ID])
    events = _capture_events(monkeypatch)

    NotificationService.publish_promotion_events(PROMOTION_ID)

    assert len(events) == 1
    assert events[0]["payload"]["description"] == ""


def test_no_subscribers_publishes_nothing(monkeypatch):
    _patch_promo_lookup(monkeypatch, _promo())
    _patch_recipients(monkeypatch, [])
    events = _capture_events(monkeypatch)

    NotificationService.publish_promotion_events(PROMOTION_ID)

    assert events == []


def test_unknown_promotion_publishes_nothing(monkeypatch):
    _patch_promo_lookup(monkeypatch, None)
    _patch_recipients(monkeypatch, [USER_A_ID, USER_B_ID])
    events = _capture_events(monkeypatch)

    NotificationService.publish_promotion_events(PROMOTION_ID)

    assert events == []
