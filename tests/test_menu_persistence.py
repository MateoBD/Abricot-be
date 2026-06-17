"""Regression test for the 'created menus vanish' report.

Proves the dispatcher write path (CognitoRestaurantService -> *Service ->
repository) actually PERSISTS menus/categories/items across sessions, and that
the apparent disappearance is purely a visibility filter: a freshly created menu
is a draft (is_active=False), so the public/active-only menu endpoint
(MenuService.get_active_menu) hides it, while the owner/admin list
(MenuService.get_all, which backs GET /restaurants/{id}/admin/menus) shows it.

Uses a real in-memory SQLite DB (no mocks) so a commit that didn't happen would
make these assertions fail.
"""

from uuid import UUID, uuid4

import pytest
from flask import Flask

from app.extensions import db
from app.repositories.menu_category_repository import MenuCategoryRepository
from app.repositories.menu_item_repository import MenuItemRepository
from app.repositories.menu_repository import MenuRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.menu_category_service import MenuCategoryService
from app.services.menu_item_service import MenuItemService
from app.services.menu_service import MenuService


@pytest.fixture
def app_ctx():
    app = Flask("test_menu_persistence")
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


def _new_restaurant():
    return RestaurantRepository.create(
        name="Abricot",
        address="Calle 123",
        phone="+54 11 4444-5555",
        city_id=uuid4(),
    )


def test_menu_category_item_persist_across_sessions_and_visibility(app_ctx):
    restaurant = _new_restaurant()
    restaurant_id = restaurant.id  # capture while the session is live
    db.session.remove()  # restaurant committed -> drop the identity map

    # --- CREATE MENU (dispatcher path: CognitoRestaurantService.create_admin_menu
    #     -> MenuService.create -> MenuRepository.create -> commit). The cognito
    #     layer parses path params to UUID, so the services receive UUIDs. ---
    menu = MenuService.create(restaurant_id, "Menu de Verano")
    menu_id = menu["id"]
    menu_uuid = UUID(menu_id)
    db.session.remove()  # simulate a fresh request/session

    persisted_menus = MenuRepository.get_all(restaurant_id)
    assert [m.name for m in persisted_menus] == ["Menu de Verano"]  # PERSISTED

    # Hidden from the public/active-only endpoint (the bug symptom): draft menu.
    assert MenuRepository.get_active(restaurant_id) is None
    assert MenuService.get_active_menu(restaurant_id) is None
    # But visible on the owner/admin list (GET /restaurants/{id}/admin/menus).
    assert any(m["id"] == menu_id for m in MenuService.get_all(restaurant_id)["data"])

    # --- CREATE CATEGORY ---
    category = MenuCategoryService.create(restaurant_id, menu_uuid, "Entradas")
    category_id = category["id"]
    category_uuid = UUID(category_id)
    db.session.remove()

    persisted_categories = MenuCategoryRepository.get_all(menu_uuid)
    assert [c.name for c in persisted_categories] == ["Entradas"]  # PERSISTED

    # --- CREATE ITEM ---
    item = MenuItemService.create(category_uuid, "Empanada", None, "150.00")
    item_id = item["id"]
    db.session.remove()

    persisted_items = MenuItemRepository.get_all(category_uuid)
    assert [i.name for i in persisted_items] == ["Empanada"]  # PERSISTED
    assert str(persisted_items[0].id) == item_id

    # --- ACTIVATE: once active, the whole tree becomes visible on the public
    #     endpoint, proving it was saved all along (not re-echoed from create). ---
    MenuService.activate(restaurant_id, menu_uuid)
    db.session.remove()

    active = MenuService.get_active_menu(restaurant_id)
    assert active is not None
    assert active["id"] == menu_id
    category_payload = active["categories"][0]
    assert category_payload["id"] == category_id
    assert category_payload["items"][0]["id"] == item_id
