import base64
import importlib.util
import json
import os
import sys
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import UUID

# Load the restaurants_service Lambda dispatcher under a unique module name so it
# does not collide with other lambdas' `handler` modules in sys.modules. `common`
# must be importable (mirrors the runtime layout from package_lambdas.sh).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LAMBDAS_DIR = os.path.join(_ROOT, "lambdas")
if _LAMBDAS_DIR not in sys.path:
    sys.path.insert(0, _LAMBDAS_DIR)

import common.api as common_api  # noqa: E402
from app.exceptions.errors import ForbiddenError  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "restaurants_service_handler",
    os.path.join(_LAMBDAS_DIR, "restaurants_service", "handler.py"),
)
handler_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(handler_module)


RID = "00000000-0000-0000-0000-000000000001"


@contextmanager
def _noop_context():
    yield


def _multipart_event(content_type: str = "image/jpeg", filename: str = "p.jpg") -> dict:
    boundary = "----abricotBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode() + b"\xff\xd8\xff\xe0FAKEIMAGEBYTES" + f"\r\n--{boundary}--\r\n".encode()
    return {
        "rawPath": f"/restaurants/{RID}/photo",
        "requestContext": {
            "http": {"method": "POST", "path": f"/restaurants/{RID}/photo"},
            "authorizer": {"jwt": {"claims": {"sub": "cognito-sub-1"}}},
        },
        "pathParameters": {"restaurantId": RID},
        "headers": {"content-type": f"multipart/form-data; boundary={boundary}"},
        "body": base64.b64encode(body).decode(),
        "isBase64Encoded": True,
    }


def test_post_photo_admin_reaches_upload_and_returns_presigned(monkeypatch):
    monkeypatch.setattr(common_api, "backend_app_context", _noop_context)
    captured: dict[str, object] = {}

    def fake_upload(*, restaurant_id, file_storage, cognito_sub, is_cognito_admin=False):
        captured["restaurant_id"] = restaurant_id
        captured["cognito_sub"] = cognito_sub
        captured["filename"] = file_storage.filename
        captured["content_type"] = file_storage.content_type
        captured["bytes"] = file_storage.read()
        return {
            "id": restaurant_id,
            "photoUrl": (
                "https://b.s3.us-east-1.amazonaws.com/restaurants/1/x.jpg"
                "?X-Amz-Signature=deadbeef123"
            ),
        }

    monkeypatch.setattr(
        handler_module.CognitoRestaurantService, "upload_photo", fake_upload
    )

    resp = handler_module.handler(_multipart_event(), None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "X-Amz-Signature=" in body["photoUrl"]
    # POST reached upload_photo with the parsed multipart file
    assert captured["restaurant_id"] == RID
    assert captured["cognito_sub"] == "cognito-sub-1"
    assert captured["filename"] == "p.jpg"
    assert captured["content_type"] == "image/jpeg"
    assert captured["bytes"] == b"\xff\xd8\xff\xe0FAKEIMAGEBYTES"


def test_post_photo_non_admin_forbidden(monkeypatch):
    monkeypatch.setattr(common_api, "backend_app_context", _noop_context)
    import app.services.cognito_restaurant_service as crs

    monkeypatch.setattr(
        crs.CognitoAuthorizationService,
        "principal_user",
        lambda cognito_sub: SimpleNamespace(id=UUID(RID)),
    )

    def _deny(**kwargs):
        raise ForbiddenError("Forbidden.", public_message="Forbidden.")

    monkeypatch.setattr(
        crs.CognitoAuthorizationService, "require_restaurant_admin", _deny
    )

    resp = handler_module.handler(_multipart_event(), None)

    assert resp["statusCode"] == 403


def test_post_photo_bad_content_type_415(monkeypatch):
    monkeypatch.setattr(common_api, "backend_app_context", _noop_context)
    import app.services.cognito_restaurant_service as crs

    monkeypatch.setattr(
        crs.CognitoAuthorizationService,
        "principal_user",
        lambda cognito_sub: SimpleNamespace(id=UUID(RID)),
    )
    monkeypatch.setattr(
        crs.CognitoAuthorizationService,
        "require_restaurant_admin",
        lambda **kwargs: None,
    )

    resp = handler_module.handler(
        _multipart_event(content_type="application/pdf", filename="x.pdf"), None
    )

    assert resp["statusCode"] == 415
