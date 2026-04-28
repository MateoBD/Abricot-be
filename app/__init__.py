import logging
import logging.config

from flask import Flask

from app.config import config, get_config_name, parse_allowed_origins
from app.logging_config import LOGGING_CONFIG

logger = logging.getLogger(__name__)


def create_app(config_name: str | None = None) -> Flask:
    """
    Application factory.

    Creates and configures the Flask application:
    - Loads the appropriate config class (production or testing).
    - Initialises all extensions: SQLAlchemy, Flask-Migrate, JWT, Bcrypt, CORS.
    - Initialises async notification worker.
    - Registers all API namespaces and blueprints.
    - Registers centralised error handlers.

    Args:
        config_name: Optional config key ("testing", "production"). Defaults to
                     the value of the ENV environment variable.

    Returns:
        A fully configured Flask application instance.
    """
    app = Flask(__name__)
    cfg_name = config_name or get_config_name()
    cfg_class = config[cfg_name]

    if hasattr(cfg_class, "validate"):
        cfg_class.validate()

    app.config.from_object(cfg_class)
    # ProductionConfig.ALLOWED_ORIGINS may have been captured at import time before load_dotenv;
    # always re-read from the environment when serving the API for real.
    if cfg_name == "production":
        app.config["ALLOWED_ORIGINS"] = parse_allowed_origins()

    _setup_logging(app)

    from app.extensions import init_extensions

    init_extensions(app)

    # Initialize async notification worker
    from app.services.notification_service import set_async_worker, _send_email_sync
    from app.services.async_queue import AsyncNotificationWorker

    worker = AsyncNotificationWorker(send_func=_send_email_sync)
    worker.start()
    set_async_worker(worker)

    # Register shutdown handler for graceful worker cleanup
    @app.teardown_appcontext
    def shutdown_worker(exception=None):
        worker.stop(timeout=5.0)

    from app.api import register_blueprints

    register_blueprints(app)

    from app.error_handlers import register_error_handlers

    register_error_handlers(app)

    return app


def _setup_logging(app: Flask) -> None:
    from flask.logging import default_handler

    app.logger.removeHandler(default_handler)
    logging.config.dictConfig(LOGGING_CONFIG)
