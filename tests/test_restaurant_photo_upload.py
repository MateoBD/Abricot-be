from types import SimpleNamespace
from uuid import UUID

import pytest
from flask import Flask

import app.services.restaurant_service as restaurant_service_module
from app.exceptions.errors import (
    NotFoundError,
    UnsupportedMediaTypeError,
    ValidationError,
)
from app.integrations.s3 import S3Client, object_key_from_value
from app.services.restaurant_service import RestaurantService


RESTAURANT_ID = UUID("00000000-0000-0000-0000-000000000001")
PHOTO_URL = "https://bucket.s3.us-east-1.amazonaws.com/restaurants/1/photo.jpg"
PHOTO_KEY = f"restaurants/{RESTAURANT_ID}/abc123def456.jpg"


class FakeRestaurant:
    def __init__(self, photo_url: str | None = None):
        self.id = RESTAURANT_ID
        self.photo_url = photo_url

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": "Abricot",
            "address": "Calle 123",
            "cityId": str(RESTAURANT_ID),
            "neighbourhoodId": None,
            "priceRangeId": None,
            "phone": "+54 11 4444-5555",
            "email": None,
            "description": None,
            "photoUrl": self.photo_url,
            "allowTableJoining": False,
            "defaultSlotDurationMinutes": 90,
            "createdAt": "2026-06-13T00:00:00+00:00",
        }


def _file(mimetype: str = "image/jpeg") -> SimpleNamespace:
    return SimpleNamespace(
        mimetype=mimetype,
        content_type=mimetype,
        filename="photo.jpg",
    )


def _stub_payload_dependencies(monkeypatch):
    monkeypatch.setattr(
        restaurant_service_module.RestaurantRepository,
        "get_cuisine_type_ids_for_restaurant",
        lambda restaurant_id: [],
    )
    monkeypatch.setattr(
        restaurant_service_module.RestaurantReviewRepository,
        "get_stats_by_restaurant_ids",
        lambda restaurant_ids: {RESTAURANT_ID: (None, 0)},
    )


def test_upload_photo_requires_file():
    with pytest.raises(ValidationError) as exc:
        RestaurantService.upload_photo(RESTAURANT_ID, None)

    assert exc.value.status_code == 400
    assert exc.value.payload == {"file": "Missing file"}


def test_upload_photo_rejects_unsupported_mime_type():
    with pytest.raises(UnsupportedMediaTypeError) as exc:
        RestaurantService.upload_photo(RESTAURANT_ID, _file("application/pdf"))

    assert exc.value.status_code == 415
    assert exc.value.code == "UNSUPPORTED_MEDIA_TYPE"
    assert exc.value.payload == {
        "file": "Allowed MIME types are image/jpeg, image/png, image/webp."
    }


def test_upload_photo_requires_existing_restaurant(monkeypatch):
    monkeypatch.setattr(
        restaurant_service_module.RestaurantRepository,
        "get_by_id",
        lambda restaurant_id: None,
    )

    with pytest.raises(NotFoundError):
        RestaurantService.upload_photo(RESTAURANT_ID, _file())


class FakeSigningS3Client:
    """Stub S3 client: upload returns the KEY, read returns a signed URL."""

    def __init__(self, calls: dict):
        self._calls = calls

    def upload_restaurant_photo(self, file_storage, restaurant_id: str) -> str:
        self._calls["file_storage"] = file_storage
        self._calls["restaurant_id"] = restaurant_id
        return PHOTO_KEY

    def generate_presigned_get_url(self, key, expires_in=None) -> str:
        self._calls["signed_key"] = key
        self._calls["expires_in"] = expires_in
        return (
            f"https://abricot-test-bucket.s3.us-east-1.amazonaws.com/{key}"
            "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Expires=3600"
            "&X-Amz-Signature=deadbeefcafebabe1234"
        )


def test_upload_photo_stores_key_and_signs_on_read(monkeypatch):
    restaurant = FakeRestaurant()
    calls: dict[str, object] = {}

    def update_photo(updated_restaurant, photo_url: str):
        updated_restaurant.photo_url = photo_url
        return updated_restaurant

    _stub_payload_dependencies(monkeypatch)
    monkeypatch.setattr(
        restaurant_service_module.RestaurantRepository,
        "get_by_id",
        lambda restaurant_id: restaurant,
    )
    monkeypatch.setattr(
        restaurant_service_module.RestaurantRepository,
        "update_photo",
        update_photo,
    )
    monkeypatch.setattr(
        restaurant_service_module.S3Client,
        "get",
        lambda: FakeSigningS3Client(calls),
    )

    file_storage = _file("image/webp")
    result = RestaurantService.upload_photo(RESTAURANT_ID, file_storage)

    assert calls["file_storage"] is file_storage
    assert calls["restaurant_id"] == str(RESTAURANT_ID)
    # the DB stores the bare object KEY, never a URL
    assert restaurant.photo_url == PHOTO_KEY
    assert "://" not in restaurant.photo_url
    # the response carries a freshly-signed presigned URL (signing query params)
    assert calls["signed_key"] == PHOTO_KEY
    assert PHOTO_KEY in result["photoUrl"]
    assert "X-Amz-Signature=" in result["photoUrl"]
    assert "X-Amz-Expires=" in result["photoUrl"]
    assert result["cuisineTypeIds"] == []
    assert result["reviewCount"] == 0


def test_restaurant_read_signs_stored_key(monkeypatch):
    restaurant = FakeRestaurant(photo_url=PHOTO_KEY)
    calls: dict[str, object] = {}

    _stub_payload_dependencies(monkeypatch)
    monkeypatch.setattr(
        restaurant_service_module.RestaurantRepository,
        "get_by_id",
        lambda restaurant_id: restaurant,
    )
    monkeypatch.setattr(
        restaurant_service_module.S3Client,
        "get",
        lambda: FakeSigningS3Client(calls),
    )

    result = RestaurantService.get_by_id(RESTAURANT_ID)

    assert calls["signed_key"] == PHOTO_KEY
    assert "X-Amz-Signature=" in result["photoUrl"]


def test_restaurant_without_photo_returns_none(monkeypatch):
    restaurant = FakeRestaurant(photo_url=None)

    class NeverSignS3Client:
        def generate_presigned_get_url(self, key, expires_in=None):
            raise AssertionError("must not sign when there is no photo")

    _stub_payload_dependencies(monkeypatch)
    monkeypatch.setattr(
        restaurant_service_module.RestaurantRepository,
        "get_by_id",
        lambda restaurant_id: restaurant,
    )
    monkeypatch.setattr(
        restaurant_service_module.S3Client,
        "get",
        lambda: NeverSignS3Client(),
    )

    result = RestaurantService.get_by_id(RESTAURANT_ID)

    assert result["photoUrl"] is None


def _app_ctx() -> Flask:
    app = Flask(__name__)
    app.config.update(
        AWS_S3_BUCKET="abricot-test-bucket",
        AWS_REGION="us-east-1",
        S3_PRESIGNED_EXPIRY=1234,
    )
    return app


def test_object_key_from_value_coerces_legacy_url_and_passes_through_key():
    app = _app_ctx()
    with app.app_context():
        # virtual-hosted legacy URL -> bare key
        assert (
            object_key_from_value(
                "https://abricot-test-bucket.s3.us-east-1.amazonaws.com/restaurants/1/p.jpg"
            )
            == "restaurants/1/p.jpg"
        )
        # path-style / localstack URL -> bucket prefix stripped
        assert (
            object_key_from_value(
                "http://localhost:4566/abricot-test-bucket/restaurants/2/q.png"
            )
            == "restaurants/2/q.png"
        )
        # already a key -> unchanged; empty -> None
        assert object_key_from_value("restaurants/3/r.webp") == "restaurants/3/r.webp"
        assert object_key_from_value(None) is None
        assert object_key_from_value("") is None


def test_generate_presigned_get_url_calls_boto_with_signing_params():
    app = _app_ctx()
    captured: dict[str, object] = {}

    class FakeBoto:
        def generate_presigned_url(self, op, Params, ExpiresIn):
            captured["op"] = op
            captured["Params"] = Params
            captured["ExpiresIn"] = ExpiresIn
            return (
                f"https://abricot-test-bucket.s3.amazonaws.com/{Params['Key']}"
                f"?X-Amz-Signature=abc123&X-Amz-Expires={ExpiresIn}"
            )

    client = S3Client()
    client._boto_client = FakeBoto()
    with app.app_context():
        url = client.generate_presigned_get_url("restaurants/1/p.jpg")

    assert captured["op"] == "get_object"
    assert captured["Params"] == {
        "Bucket": "abricot-test-bucket",
        "Key": "restaurants/1/p.jpg",
    }
    # expiry comes from S3_PRESIGNED_EXPIRY config when not overridden
    assert captured["ExpiresIn"] == 1234
    assert "X-Amz-Signature=" in url
