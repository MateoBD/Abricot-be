from types import SimpleNamespace
from uuid import UUID

import pytest

import app.services.restaurant_service as restaurant_service_module
from app.exceptions.errors import (
    NotFoundError,
    UnsupportedMediaTypeError,
    ValidationError,
)
from app.services.restaurant_service import RestaurantService


RESTAURANT_ID = UUID("00000000-0000-0000-0000-000000000001")
PHOTO_URL = "https://bucket.s3.us-east-1.amazonaws.com/restaurants/1/photo.jpg"


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


def test_upload_photo_uploads_to_s3_and_updates_restaurant(monkeypatch):
    restaurant = FakeRestaurant()
    uploaded: dict[str, object] = {}

    class FakeS3Client:
        def upload_restaurant_photo(self, file_storage, restaurant_id: str) -> str:
            uploaded["file_storage"] = file_storage
            uploaded["restaurant_id"] = restaurant_id
            return PHOTO_URL

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
        lambda: FakeS3Client(),
    )

    file_storage = _file("image/webp")
    result = RestaurantService.upload_photo(RESTAURANT_ID, file_storage)

    assert uploaded == {
        "file_storage": file_storage,
        "restaurant_id": str(RESTAURANT_ID),
    }
    assert result["photoUrl"] == PHOTO_URL
    assert result["cuisineTypeIds"] == []
    assert result["reviewCount"] == 0
