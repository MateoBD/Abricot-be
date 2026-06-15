"""Promos must change the price shown on menu read paths.

Bug: active promos targeting menu items had no effect -- customer Menú tab and
owner menu detail returned base prices. These tests pin the fix: the read paths
(MenuService.get_active_menu / get_detail) enrich each item with `discountedPrice`
and `discount`, computed from the active promos targeting it.

Real in-memory SQLite (no mocks), same fixture style as test_menu_persistence.
"""

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from flask import Flask

from app.extensions import db
from app.models.enums import DiscountType
from app.models.promotion import PromotionModel
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.menu_category_service import MenuCategoryService
from app.services.menu_item_service import MenuItemService
from app.services.menu_service import MenuService
from app.services.promotion_pricing import apply_promo, best_promo
from app.services.promotion_service import PromotionService

TODAY = date.today()
YESTERDAY = (TODAY - timedelta(days=1)).isoformat()
TOMORROW = (TODAY + timedelta(days=1)).isoformat()
LAST_WEEK = (TODAY - timedelta(days=7)).isoformat()
THREE_DAYS_AGO = (TODAY - timedelta(days=3)).isoformat()


@pytest.fixture
def app_ctx():
    app = Flask("test_promotion_pricing")
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


def _seed_menu():
    """Active menu with one category and three items. Returns ids."""
    restaurant = RestaurantRepository.create(
        name="Abricot", address="Calle 123", phone="+54 11 4444-5555", city_id=uuid4()
    )
    restaurant_id = restaurant.id
    menu = MenuService.create(restaurant_id, "Carta")
    menu_uuid = UUID(menu["id"])
    category = MenuCategoryService.create(restaurant_id, menu_uuid, "Platos")
    category_uuid = UUID(category["id"])
    pct_item = MenuItemService.create(category_uuid, "Pizza", None, "100.00")
    fixed_item = MenuItemService.create(category_uuid, "Pasta", None, "200.00")
    plain_item = MenuItemService.create(category_uuid, "Ensalada", None, "80.00")
    MenuService.activate(restaurant_id, menu_uuid)
    db.session.remove()
    return {
        "restaurant_id": restaurant_id,
        "pct_item": pct_item["id"],
        "fixed_item": fixed_item["id"],
        "plain_item": plain_item["id"],
    }


def _items_by_id(menu_payload: dict) -> dict[str, dict]:
    return {i["id"]: i for i in menu_payload["categories"][0]["items"]}


# --- pure pricing math -------------------------------------------------------


def _promo(discount_type: DiscountType, value: str) -> PromotionModel:
    return PromotionModel(
        restaurant_id=uuid4(),
        title="x",
        discount_type=discount_type,
        discount_value=Decimal(value),
        start_date=TODAY,
        end_date=TODAY,
    )


def test_apply_promo_percentage_fixed_and_free():
    price = Decimal("100.00")
    assert apply_promo(price, _promo(DiscountType.PERCENTAGE, "20")) == Decimal("80.00")
    assert apply_promo(price, _promo(DiscountType.FIXED_AMOUNT, "30")) == Decimal("70.00")
    assert apply_promo(price, _promo(DiscountType.FREE_ITEM, "0")) == Decimal("0.00")
    # fixed discount larger than price floors at 0, never negative
    assert apply_promo(price, _promo(DiscountType.FIXED_AMOUNT, "150")) == Decimal("0.00")


def test_best_promo_picks_lowest_effective_price():
    price = Decimal("100.00")
    promos = [_promo(DiscountType.PERCENTAGE, "10"), _promo(DiscountType.FIXED_AMOUNT, "50")]
    effective, chosen = best_promo(price, promos)
    assert effective == Decimal("50.00")
    assert chosen.discount_type == DiscountType.FIXED_AMOUNT
    assert best_promo(price, []) is None


# --- end-to-end read paths ---------------------------------------------------


def test_active_percentage_and_fixed_promos_apply_on_customer_menu(app_ctx):
    ids = _seed_menu()
    rid = ids["restaurant_id"]

    PromotionService.create(
        rid, "20% off", None, "PERCENTAGE", "20", YESTERDAY, TOMORROW,
        menu_item_ids=[ids["pct_item"]],
    )
    PromotionService.create(
        rid, "$50 off", None, "FIXED_AMOUNT", "50", YESTERDAY, TOMORROW,
        menu_item_ids=[ids["fixed_item"]],
    )
    db.session.remove()

    items = _items_by_id(MenuService.get_active_menu(rid))

    pct = items[ids["pct_item"]]
    assert pct["price"] == "100.00"  # base unchanged
    assert pct["discountedPrice"] == "80.00"  # 100 - 20%
    assert pct["discount"]["discountType"] == "PERCENTAGE"
    assert pct["discount"]["title"] == "20% off"

    fixed = items[ids["fixed_item"]]
    assert fixed["price"] == "200.00"
    assert fixed["discountedPrice"] == "150.00"  # 200 - 50
    assert fixed["discount"]["discountType"] == "FIXED_AMOUNT"


def test_expired_promo_leaves_base_price(app_ctx):
    ids = _seed_menu()
    rid = ids["restaurant_id"]

    PromotionService.create(
        rid, "old sale", None, "PERCENTAGE", "50", LAST_WEEK, THREE_DAYS_AGO,
        menu_item_ids=[ids["pct_item"]],
    )
    db.session.remove()

    items = _items_by_id(MenuService.get_active_menu(rid))
    pct = items[ids["pct_item"]]
    assert pct["price"] == "100.00"
    assert pct["discountedPrice"] is None
    assert pct["discount"] is None


def test_item_without_promo_has_null_discount(app_ctx):
    ids = _seed_menu()
    rid = ids["restaurant_id"]
    PromotionService.create(
        rid, "20% off", None, "PERCENTAGE", "20", YESTERDAY, TOMORROW,
        menu_item_ids=[ids["pct_item"]],
    )
    db.session.remove()

    items = _items_by_id(MenuService.get_active_menu(rid))
    plain = items[ids["plain_item"]]
    assert plain["discountedPrice"] is None
    assert plain["discount"] is None
