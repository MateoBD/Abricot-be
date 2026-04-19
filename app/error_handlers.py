import logging

from flask import Flask, jsonify
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from app.exceptions.errors import AppError
from app.extensions import db

logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def handle_app_error(e: AppError):
        return jsonify({"message": e.message, "code": e.code, "errors": e.payload}), e.status_code

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(e: IntegrityError):
        db.session.rollback()
        logger.warning(f"IntegrityError: {e}")
        return jsonify({"message": "Resource already exists.", "code": "CONFLICT", "errors": {}}), 409

    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        logger.warning(f"HTTPException {e.code}: {e.description}")
        return jsonify({"message": e.description, "code": type(e).__name__, "errors": {}}), e.code

    @app.errorhandler(ValueError)
    def handle_value_error(e: ValueError):
        logger.warning(f"ValueError: {e}")
        return jsonify({"message": str(e), "code": "VALUE_ERROR", "errors": {}}), 400

    @app.errorhandler(Exception)
    def handle_unexpected(e: Exception):
        logger.exception("Unexpected error")
        return jsonify({"message": "Internal server error.", "code": "INTERNAL_ERROR", "errors": {}}), 500
