import logging

from werkzeug.exceptions import BadRequest

from app.error_handlers import app_error_payload, http_exception_payload
from app.exceptions.errors import NotFoundError, UnauthorizedError, ValidationError
from app.logging_config import AbricotConsoleFormatter


def test_not_found_payload_hides_internal_detail():
    payload, status_code = app_error_payload(
        NotFoundError(
            "Restaurant with id=00000000-0000-0000-0000-000000000001 not found."
        )
    )

    assert status_code == 404
    assert payload == {
        "message": "We could not find that resource.",
        "code": "NOT_FOUND",
        "errors": {},
    }


def test_validation_payload_keeps_specific_user_message():
    payload, status_code = app_error_payload(
        ValidationError(
            "Password must be at least 8 characters.",
            {"password": "Too short"},
        )
    )

    assert status_code == 400
    assert payload == {
        "message": "Password must be at least 8 characters.",
        "code": "VALIDATION_ERROR",
        "errors": {"password": "Too short"},
    }


def test_app_error_can_override_public_message():
    payload, status_code = app_error_payload(
        UnauthorizedError(
            "JWT expired at 2026-05-12T01:00:00Z.",
            public_message="Your session expired. Please sign in again.",
        )
    )

    assert status_code == 401
    assert payload["message"] == "Your session expired. Please sign in again."
    assert payload["code"] == "UNAUTHORIZED"


def test_http_exception_payload_keeps_field_errors_without_raw_description():
    error = BadRequest("Raw schema details that should stay in backend logs.")
    error.data = {"errors": {"email": "'email' is a required property"}}

    payload, status_code = http_exception_payload(error)

    assert status_code == 400
    assert payload == {
        "message": "Please check the request and try again.",
        "code": "BAD_REQUEST",
        "errors": {"email": "'email' is a required property"},
    }


def test_api_error_formatter_uses_readable_block():
    record = logging.LogRecord(
        "app.error_handlers",
        logging.WARNING,
        __file__,
        12,
        "API error handled",
        (),
        None,
    )
    record.log_style = "api_error"
    record.api_status_code = 404
    record.api_error_code = "NOT_FOUND"
    record.api_method = "GET"
    record.api_path = "/restaurants/missing"
    record.api_query = "page=1"
    record.api_origin = "http://localhost:5173"
    record.api_client_ip = "127.0.0.1"
    record.api_public_message = "We could not find that resource."
    record.api_detail = "NotFoundError: Restaurant with id=missing not found."
    record.api_errors = {}
    record.api_source = "app/services/restaurant_service.py:136"

    output = AbricotConsoleFormatter().format(record)

    assert "[API ERROR]" in output
    assert "Status  : 404 NOT_FOUND" in output
    assert "Request : GET /restaurants/missing?page=1" in output
    assert "Public  : We could not find that resource." in output
    assert "Detail  : NotFoundError: Restaurant with id=missing not found." in output
