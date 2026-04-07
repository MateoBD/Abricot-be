import logging

from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from project.exceptions.auth_exception import AuthException
from project.exceptions.restaurant_exception import RestaurantException

logger = logging.getLogger(__name__)


def register_api_handlers(api):
    """
    Registers error handlers on the Flask-RESTX Api instance.

    Handles:
        - AuthException: Business-logic auth errors (400).
        - RestaurantException: Business-logic restaurant errors (400).
        - IntegrityError: Database constraint violations (400).
        - HTTPException: Standard HTTP errors (preserves original status code).
        - ValueError: Bad input values (400).
        - Exception: Catch-all for unexpected errors (500).
    """

    @api.errorhandler(AuthException)
    def handle_auth_exception(e):
        logger.warning(f"AuthException: {e}")
        return {"message": str(e), "errors": e.payload}, 400

    @api.errorhandler(RestaurantException)
    def handle_restaurant_exception(e):
        logger.warning(f"RestaurantException: {e}")
        return {"message": str(e), "errors": e.payload}, 400

    @api.errorhandler(IntegrityError)
    def handle_integrity_error(e):
        original_message = e.orig.args[1]
        logger.info(f"IntegrityError: {e}")
        return {
            "message": str(original_message),
            "errors": [
                {"apiCode": "SQLAlchemyError", "message": str(original_message)}
            ],
        }, 400

    @api.errorhandler(HTTPException)
    def handle_http_exception(e):
        logger.warning(f"HTTPException: {e}")
        return {
            "message": str(e),
            "errors": [{"apiCode": type(e).__name__, "message": str(e)}],
        }, e.code

    @api.errorhandler(ValueError)
    def handle_value_error(e):
        logger.warning(f"ValueError: {e}")
        return {
            "message": str(e),
            "errors": [{"apiCode": "ValueError", "message": str(e)}],
        }, 400

    @api.errorhandler(Exception)
    def handle_unexpected_exception(e):
        logger.exception(f"Unexpected exception: {e}")
        return {
            "message": str(e),
            "errors": [{"apiCode": type(e).__name__, "message": str(e)}],
        }, 500


def register_app_handlers(app):
    """Registers a catch-all error handler directly on the Flask app instance."""

    @app.errorhandler(Exception)
    def handle_unexpected_exception(e):
        logger.exception(f"Unexpected exception: {e}")
        return {
            "message": str(e),
            "errors": [{"apiCode": type(e).__name__, "message": str(e)}],
        }, 500
