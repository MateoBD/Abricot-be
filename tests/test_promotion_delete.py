"""Deleting a promotion must succeed even when it has child rows.

Bug: "No se pudo eliminar la promocion". promotions.id has two FK children
(promotion_items, notification_events). On Postgres a leftover child row makes
the promo delete raise IntegrityError -> the dispatcher returns 500.

SQLite ignores FK constraints unless PRAGMA foreign_keys=ON, so each delete test
flips it on right before the act to mimic Postgres -- otherwise these would pass
even with the bug present.

Real in-memory SQLite (no mocks), same fixture style as test_menu_persistence.
"""

from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest
from flask import Flask
from sqlalchemy import text

from app.exceptions.errors import NotFoundError
from app.extensions import db
from app.models.notification_event import (
    NotificationEventStatus,
    NotificationEventType,
)
from app.repositories.notification_event_repository import NotificationEventRepository
from app.repositories.promotion_item_repository import PromotionItemRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.menu_category_service import MenuCategoryService
from app.services.menu_item_service import MenuItemService
from app.services.menu_service import MenuService
from app.services.promotion_service import PromotionService

TODAY = date.today()
YESTERDAY = (TODAY - timedelta(days=1)).isoformat()
TOMORROW = (TODAY + timedelta(days=1)).isoformat()


@pytest.fixture
def app_ctx():
    app = Flask("test_promotion_delete")
    app.config.update(
        SQLALCHEMY_DATABASE_URI="sqlite+pysqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        AWS_S3_BUCKET="",
        AWS_REGION="us-east-1",
    )
    db.init_app(app)
    with app.app_context():
        import app.models  # noqa: F401  -- register every model on db.metadata

        db.create_all()
        try:
            yield app
        finally:
            db.session.remove()
            db.drop_all()


def _enforce_foreign_keys():
    """Make SQLite behave like Postgres for the delete (RESTRICT on children)."""
    db.session.execute(text("PRAGMA foreign_keys=ON"))


def _seed_promo_with_item_link():
    """Restaurant + active promo targeting one menu item. Returns ids."""
    restaurant = RestaurantRepository.create(
        name="Abricot", address="Calle 123", phone="+54 11 4444-5555", city_id=uuid4()
    )
    rid = restaurant.id
    menu = MenuService.create(rid, "Carta")
    menu_uuid = UUID(menu["id"])
    category = MenuCategoryService.create(rid, menu_uuid, "Platos")
    item = MenuItemService.create(UUID(category["id"]), "Pizza", None, "100.00")
    promo = PromotionService.create(
        rid, "20% off", None, "PERCENTAGE", "20", YESTERDAY, TOMORROW,
        menu_item_ids=[item["id"]],
    )
    return {"restaurant_id": rid, "promo_id": UUID(promo["id"]), "item_id": item["id"]}


def test_delete_promo_with_item_links_removes_it(app_ctx):
    ids = _seed_promo_with_item_link()
    rid, pid = ids["restaurant_id"], ids["promo_id"]
    # promo really targets the item before delete
    assert PromotionItemRepository.list_menu_item_ids(pid) == [UUID(ids["item_id"])]
    db.session.remove()

    _enforce_foreign_keys()
    PromotionService.delete(rid, pid)  # must not raise IntegrityError
    db.session.remove()

    # gone on re-read
    with pytest.raises(NotFoundError):
        PromotionService.get_by_id(rid, pid)
    assert all(p["id"] != str(pid) for p in PromotionService.get_all_for_admin(rid)["data"])
    # child links cleaned up too
    assert PromotionItemRepository.list_menu_item_ids(pid) == []


def test_delete_promo_keeps_notification_audit_and_succeeds(app_ctx):
    ids = _seed_promo_with_item_link()
    rid, pid = ids["restaurant_id"], ids["promo_id"]

    # an audit row references the promo (the second FK child)
    event = NotificationEventRepository.log_event(
        event_type=NotificationEventType.PROMOTION_NOTIFICATION,
        recipient_email="user@example.com",
        subject="Nueva promo",
        body="...",
        status=NotificationEventStatus.SENT,
        restaurant_id=rid,
        promotion_id=pid,
    )
    event_id = event.id
    db.session.remove()

    _enforce_foreign_keys()
    PromotionService.delete(rid, pid)  # would 500 without nulling the audit FK
    db.session.remove()

    with pytest.raises(NotFoundError):
        PromotionService.get_by_id(rid, pid)
    # audit row survives, its dangling promo ref nulled
    audit = NotificationEventRepository.get_by_id(event_id)
    assert audit is not None
    assert audit.promotion_id is None
