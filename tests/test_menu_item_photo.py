from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from flask import Flask

import app.services.menu_item_service as menu_item_service_module
from app.services.menu_item_service import MenuItemService, menu_item_payload


ITEM_ID = UUID("00000000-0000-0000-0000-0000000000a1")
CATEGORY_ID = UUID("00000000-0000-0000-0000-0000000000b2")
ITEM_KEY = f"menu-items/{ITEM_ID}/abc123def456.jpg"


class FakeItem:
    def __init__(self, photo_url: str | None = None):
        self.id = ITEM_ID
        self.category_id = CATEGORY_ID
        self.photo_url = photo_url

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "categoryId": str(self.category_id),
            "name": "Milanesa",
            "description": None,
            "price": "1000.00",
            "isAvailable": True,
            "photoUrl": self.photo_url,
        }


class FakeSigningS3Client:
    def __init__(self, calls: dict):
        self._calls = calls

    def upload_menu_item_photo(self, file_storage, item_id) -> str:
        self._calls["file_storage"] = file_storage
        self._calls["item_id"] = item_id
        return ITEM_KEY

    def generate_presigned_get_url(self, key, expires_in=None) -> str:
        self._calls["signed_key"] = key
        return (
            f"https://abricot-test-bucket.s3.us-east-1.amazonaws.com/{key}"
            "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Expires=3600"
            "&X-Amz-Signature=deadbeefcafebabe1234"
        )


def _file(mimetype: str = "image/jpeg") -> SimpleNamespace:
    return SimpleNamespace(mimetype=mimetype, content_type=mimetype, filename="m.jpg")


def test_menu_item_payload_signs_stored_key(monkeypatch):
    calls: dict[str, object] = {}
    monkeypatch.setattr(
        menu_item_service_module.S3Client, "get", lambda: FakeSigningS3Client(calls)
    )

    payload = menu_item_payload(FakeItem(photo_url=ITEM_KEY))

    assert calls["signed_key"] == ITEM_KEY
    assert "://" not in ITEM_KEY  # stored value is a bare key
    assert ITEM_KEY in payload["photoUrl"]
    assert "X-Amz-Signature=" in payload["photoUrl"]


def test_menu_item_payload_without_photo_returns_none(monkeypatch):
    class NeverSign:
        def generate_presigned_get_url(self, key, expires_in=None):
            raise AssertionError("must not sign when there is no photo")

    monkeypatch.setattr(menu_item_service_module.S3Client, "get", lambda: NeverSign())

    assert menu_item_payload(FakeItem(photo_url=None))["photoUrl"] is None


def test_upload_photo_stores_key_and_signs_on_read(monkeypatch):
    item = FakeItem()
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        menu_item_service_module.MenuItemRepository,
        "get_by_id",
        lambda item_id: item,
    )
    monkeypatch.setattr(
        menu_item_service_module.MenuItemRepository,
        "save",
        lambda saved_item: saved_item,
    )
    monkeypatch.setattr(
        menu_item_service_module.S3Client, "get", lambda: FakeSigningS3Client(calls)
    )

    result = MenuItemService.upload_photo(ITEM_ID, _file("image/webp"))

    # DB stores the bare object KEY, never a URL
    assert item.photo_url == ITEM_KEY
    assert "://" not in item.photo_url
    # response carries a freshly-signed presigned URL
    assert calls["signed_key"] == ITEM_KEY
    assert ITEM_KEY in result["photoUrl"]
    assert "X-Amz-Signature=" in result["photoUrl"]


def test_get_by_id_signs_stored_key(monkeypatch):
    item = FakeItem(photo_url=ITEM_KEY)
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        menu_item_service_module.MenuItemRepository,
        "get_by_id",
        lambda item_id: item,
    )
    monkeypatch.setattr(
        menu_item_service_module.S3Client, "get", lambda: FakeSigningS3Client(calls)
    )

    result = MenuItemService.get_by_id(ITEM_ID)

    assert calls["signed_key"] == ITEM_KEY
    assert "X-Amz-Signature=" in result["photoUrl"]


def test_menu_item_payload_coerces_legacy_url(monkeypatch):
    calls: dict[str, object] = {}
    monkeypatch.setattr(
        menu_item_service_module.S3Client, "get", lambda: FakeSigningS3Client(calls)
    )

    legacy = "https://abricot-test-bucket.s3.us-east-1.amazonaws.com/menu-items/1/x.jpg"
    app = Flask(__name__)
    app.config.update(AWS_S3_BUCKET="abricot-test-bucket")
    with app.app_context():
        payload = menu_item_payload(FakeItem(photo_url=legacy))

    # legacy full URL coerced to the bare key before signing
    assert calls["signed_key"] == "menu-items/1/x.jpg"
    assert "X-Amz-Signature=" in payload["photoUrl"]
