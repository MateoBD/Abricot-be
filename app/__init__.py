import logging
import logging.config

from flask import Flask

from app.config import config, get_config_name
from app.logging_config import LOGGING_CONFIG

logger = logging.getLogger(__name__)


def create_app(config_name: str | None = None) -> Flask:
    """
    Application factory.

    Creates and configures the Flask application:
    - Loads the appropriate config class (production or testing).
    - Initialises all extensions: SQLAlchemy, Flask-Migrate, JWT, Bcrypt, CORS.
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

    _setup_logging(app)

    from app.extensions import init_extensions

    init_extensions(app)

    from app.api import register_blueprints

    register_blueprints(app)

    from app.error_handlers import register_error_handlers

    register_error_handlers(app)

    return app


def _setup_logging(app: Flask) -> None:
    from flask.logging import default_handler

    app.logger.removeHandler(default_handler)
    logging.config.dictConfig(LOGGING_CONFIG)
