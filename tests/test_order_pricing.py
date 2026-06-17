"""Orders must charge the EFFECTIVE (promo-discounted) price, server-side, and
each line must snapshot the dish NAME so the order detail reads a name (not a raw
item_id) and stays an immutable record of what was bought + charged.

Bugs being pinned:
 1. Checkout summed the BASE price -- a $100 item under a $50 promo was ordered at
    $100. Now each line is priced with the current active promos (best_promo), the
    same lookup the menu read path uses.
 2. Order detail rendered the item_id ("Ítem 019ecbea"). Now the line snapshots
    item_name; the serializer returns it. menu_item_id is kept for traceability.

Real in-memory SQLite (no mocks), same fixture style as test_promotion_pricing.
"""

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from flask import Flask

from app.extensions import db
from app.repositories.menu_item_repository import MenuItemRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.menu_category_service import MenuCategoryService
from app.services.menu_item_service import MenuItemService
from app.services.menu_service import MenuService
from app.services.order_service import OrderService
from app.services.promotion_service import PromotionService

TODAY = date.today()
YESTERDAY = (TODAY - timedelta(days=1)).isoformat()
TOMORROW = (TODAY + timedelta(days=1)).isoformat()


@pytest.fixture
def app_ctx():
    app = Flask("test_order_pricing")
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


def _seed():
    """Active menu with two items + a customer. Returns ids."""
    from app.models.enums import UserRole
    from app.models.user import UserModel

    user = UserModel(
        email="diner@example.com",
        password_hash="x",
        name="Di",
        surname="Ner",
        role=UserRole.CUSTOMER,
    )
    db.session.add(user)
    db.session.commit()
    user_id = user.id

    restaurant = RestaurantRepository.create(
        name="Abricot", address="Calle 123", phone="+54 11 4444-5555", city_id=uuid4()
    )
    restaurant_id = restaurant.id
    menu = MenuService.create(restaurant_id, "Carta")
    menu_uuid = UUID(menu["id"])
    category = MenuCategoryService.create(restaurant_id, menu_uuid, "Platos")
    category_uuid = UUID(category["id"])
    promo_item = MenuItemService.create(category_uuid, "Jeff's Flan", None, "1000.00")
    plain_item = MenuItemService.create(category_uuid, "Pizza", None, "200.00")
    MenuService.activate(restaurant_id, menu_uuid)
    db.session.remove()
    return {
        "restaurant_id": restaurant_id,
        "user_id": user_id,
        "promo_item": UUID(promo_item["id"]),
        "plain_item": UUID(plain_item["id"]),
    }


def _line_by_item(detail: dict, item_id: UUID) -> dict:
    return {UUID(i["menuItemId"]): i for i in detail["items"]}[item_id]


def test_order_line_uses_effective_price_and_item_name(app_ctx):
    ids = _seed()
    rid = ids["restaurant_id"]

    # $500 off Jeff's Flan ($1000 -> $500 effective).
    PromotionService.create(
        rid, "Flan Day", None, "FIXED_AMOUNT", "500", YESTERDAY, TOMORROW,
        menu_item_ids=[ids["promo_item"]],
    )
    db.session.remove()

    created = OrderService.create(
        restaurant_id=rid,
        user_id=ids["user_id"],
        items=[{"menuItemId": str(ids["promo_item"]), "quantity": 2}],
    )
    order_id = UUID(created["id"])
    db.session.remove()

    # Total = effective 500 * 2, NOT base 1000 * 2.
    assert created["totalAmount"] == "1000.00"

    detail = OrderService.get_by_id_for_restaurant_admin(order_id, rid)
    line = _line_by_item(detail, ids["promo_item"])
    assert line["itemName"] == "Jeff's Flan"          # name, not the id
    assert line["unitPrice"] == "500.00"              # effective
    assert line["basePrice"] == "1000.00"             # pre-discount snapshot
    assert line["appliedPromotionId"] is not None
    assert detail["totalAmount"] == "1000.00"


def test_item_without_promo_uses_base_price(app_ctx):
    ids = _seed()
    rid = ids["restaurant_id"]

    created = OrderService.create(
        restaurant_id=rid,
        user_id=ids["user_id"],
        items=[{"menuItemId": str(ids["plain_item"]), "quantity": 1}],
    )
    order_id = UUID(created["id"])
    db.session.remove()

    assert created["totalAmount"] == "200.00"
    detail = OrderService.get_by_id_for_restaurant_admin(order_id, rid)
    line = _line_by_item(detail, ids["plain_item"])
    assert line["itemName"] == "Pizza"
    assert line["unitPrice"] == "200.00"
    assert line["basePrice"] == "200.00"
    assert line["appliedPromotionId"] is None


def test_snapshot_survives_menu_item_rename_and_price_change(app_ctx):
    ids = _seed()
    rid = ids["restaurant_id"]

    PromotionService.create(
        rid, "Flan Day", None, "FIXED_AMOUNT", "500", YESTERDAY, TOMORROW,
        menu_item_ids=[ids["promo_item"]],
    )
    db.session.remove()

    created = OrderService.create(
        restaurant_id=rid,
        user_id=ids["user_id"],
        items=[{"menuItemId": str(ids["promo_item"]), "quantity": 1}],
    )
    order_id = UUID(created["id"])
    db.session.remove()

    # Rename + reprice the menu item AFTER the order exists.
    item = MenuItemRepository.get_by_id(ids["promo_item"])
    item.name = "Renamed Dessert"
    item.price = Decimal("9999.00")
    db.session.commit()
    db.session.remove()

    detail = OrderService.get_by_id_for_restaurant_admin(order_id, rid)
    line = _line_by_item(detail, ids["promo_item"])
    assert line["itemName"] == "Jeff's Flan"   # frozen at order time
    assert line["unitPrice"] == "500.00"        # frozen effective price
    assert detail["totalAmount"] == "500.00"
