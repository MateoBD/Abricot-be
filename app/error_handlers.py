import logging
from pathlib import Path

from flask import Flask, has_request_context, jsonify, request
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from app.exceptions.errors import AppError
from app.extensions import db

logger = logging.getLogger(__name__)


HTTP_ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "UNPROCESSABLE_ENTITY",
    429: "RATE_LIMITED",
}

HTTP_PUBLIC_MESSAGES = {
    400: "Please check the request and try again.",
    401: "Please sign in to continue.",
    403: "You do not have permission to do that.",
    404: "We could not find that endpoint or resource.",
    405: "That action is not available for this endpoint.",
    409: "That request conflicts with the current state.",
    415: "Please send the request in a supported format.",
    422: "Please check the request and try again.",
    429: "Too many requests. Please wait a moment and try again.",
}

INTERNAL_PUBLIC_MESSAGE = "Something went wrong on our side. Please try again."


def app_error_payload(error: AppError) -> tuple[dict, int]:
    return _payload(
        message=error.public_message,
        code=error.code,
        errors=error.payload,
    ), error.status_code


def integrity_error_payload(error: IntegrityError) -> tuple[dict, int]:
    db.session.rollback()
    return _payload(
        message="That record already exists or conflicts with existing data.",
        code="CONFLICT",
        errors={},
    ), 409


def http_exception_payload(error: HTTPException) -> tuple[dict, int]:
    status_code = error.code or 500
    error_data = getattr(error, "data", {}) or {}
    errors = error_data.get("errors", {}) if isinstance(error_data, dict) else {}
    return _payload(
        message=HTTP_PUBLIC_MESSAGES.get(status_code, INTERNAL_PUBLIC_MESSAGE),
        code=HTTP_ERROR_CODES.get(status_code, type(error).__name__.upper()),
        errors=errors,
    ), status_code


def value_error_payload(error: ValueError) -> tuple[dict, int]:
    return _payload(
        message="Some data is invalid. Please check it and try again.",
        code="VALUE_ERROR",
        errors={},
    ), 400


def unexpected_error_payload(error: Exception) -> tuple[dict, int]:
    return _payload(
        message=INTERNAL_PUBLIC_MESSAGE,
        code="INTERNAL_ERROR",
        errors={},
    ), 500


def log_handled_error(error: Exception, payload: dict, status_code: int) -> None:
    if status_code >= 500:
        level = logging.ERROR
    elif status_code == 404:
        level = logging.INFO
    else:
        level = logging.WARNING
    logger.log(
        level,
        "API error handled",
        exc_info=status_code >= 500,
        extra={
            "log_style": "api_error",
            "api_status_code": status_code,
            "api_error_code": payload["code"],
            "api_public_message": payload["message"],
            "api_errors": payload.get("errors") or {},
            "api_detail": _exception_detail(error),
            "api_source": _exception_source(error),
            **_request_log_context(),
        },
    )


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        payload, status_code = app_error_payload(error)
        log_handled_error(error, payload, status_code)
        return jsonify(payload), status_code

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error: IntegrityError):
        payload, status_code = integrity_error_payload(error)
        log_handled_error(error, payload, status_code)
        return jsonify(payload), status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        payload, status_code = http_exception_payload(error)
        log_handled_error(error, payload, status_code)
        return jsonify(payload), status_code

    @app.errorhandler(ValueError)
    def handle_value_error(error: ValueError):
        payload, status_code = value_error_payload(error)
        log_handled_error(error, payload, status_code)
        return jsonify(payload), status_code

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception):
        payload, status_code = unexpected_error_payload(error)
        log_handled_error(error, payload, status_code)
        return jsonify(payload), status_code


def _payload(message: str, code: str, errors: dict) -> dict:
    return {
        "message": message,
        "code": code,
        "errors": errors,
    }


def _exception_detail(error: Exception) -> str:
    detail = f"{type(error).__name__}: {error}"
    if error.__cause__:
        detail = (
            f"{detail} | caused by "
            f"{type(error.__cause__).__name__}: {error.__cause__}"
        )
    return detail


def _exception_source(error: Exception) -> str:
    traceback = error.__traceback__
    last_frame = None
    while traceback:
        last_frame = traceback
        traceback = traceback.tb_next

    if not last_frame:
        return "-"

    file_path = Path(last_frame.tb_frame.f_code.co_filename)
    try:
        file_path = file_path.relative_to(Path.cwd())
    except ValueError:
        file_path = Path(file_path.name)
    return f"{file_path}:{last_frame.tb_lineno}"


def _request_log_context() -> dict:
    if not has_request_context():
        return {
            "api_method": "-",
            "api_path": "-",
            "api_query": "",
            "api_origin": "-",
            "api_client_ip": "-",
            "api_user_agent": "-",
        }

    return {
        "api_method": request.method,
        "api_path": request.path,
        "api_query": request.query_string.decode("utf-8", errors="replace"),
        "api_origin": request.headers.get("Origin", "-"),
        "api_client_ip": request.headers.get(
            "X-Forwarded-For",
            request.remote_addr or "-",
        ),
        "api_user_agent": request.headers.get("User-Agent", "-"),
    }
