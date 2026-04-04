import logging

from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from project.exceptions.template_exception import TemplateException

logger = logging.getLogger(__name__)


def register_api_handlers(api):
    @api.errorhandler(TemplateException)
    def handle_template_exception(e):
        logger.error(f"Template exception: {str(e)}")
        return {"message": str(e), "errors": e.payload}, 400

    @api.errorhandler(IntegrityError)
    def handle_integrity_error_exception(e):
        original_message = e.orig.args[1]
        logger.info(f"SQL Alchemy exception: {str(e)}")
        return {
            "message": str(original_message),
            "errors": [
                {"apiCode": "SQLAlchemyError", "message": str(original_message)}
            ],
        }, 400

    @api.errorhandler(HTTPException)
    def handle_http_exception(e):
        logger.warning(f"HTTPException thrown: {str(e)}")
        return {
            "message": str(e),
            "errors": [{"apiCode": str(type(e).__name__), "message": str(e)}],
        }, e.code

    @api.errorhandler(ValueError)
    def handle_value_error(e):
        logger.warning(f"ValueError thrown: {str(e)}")
        return {
            "message": str(e),
            "errors": [{"apiCode": "ValueError", "message": str(e)}],
        }, 400

    @api.errorhandler(Exception)
    def handle_unexpected_exception(e):
        logger.exception(f"Unexpected exception caught: {str(e)}")
        return {
            "message": str(e),
            "errors": [{"apiCode": str(type(e).__name__), "message": str(e)}],
        }, 500


def register_app_handlers(api):
    @api.errorhandler(Exception)
    def handle_unexpected_exception(e):
        logger.exception(f"Unexpected exception caught: {str(e)}")
        return {
            "message": str(e),
            "errors": [{"apiCode": str(type(e).__name__), "message": str(e)}],
        }, 500
