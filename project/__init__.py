# ruff: noqa F401
import logging
import logging.config
import os

from dotenv import load_dotenv
from flask import Blueprint, Flask
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_restx import Api
from flask_sqlalchemy import SQLAlchemy

from project.error_handlers.common_handlers import (
    register_api_handlers,
    register_app_handlers,
)
from project.logging_config import LOGGING_CONFIG

load_dotenv()

logger = logging.getLogger(__name__)

bcrypt = Bcrypt()
cors = CORS(
    allow_headers=["Authorization", "Content-Type"],
    supports_credentials=True,
    # By default allow all origins. Adjust in production as needed.
    origins=["*"],
)
db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()


def create_app(config_obj=None):
    """
    Application factory.

    Creates and configures the Flask application:
    - Configures the database connection (MySQL in production, SQLite in testing).
    - Registers all blueprints and namespaces.
    - Initialises extensions: SQLAlchemy, Flask-Migrate, Flask-JWT-Extended,
      Flask-Bcrypt, and Flask-CORS.

    Args:
        config_obj: Optional configuration object to override defaults.

    Returns:
        A configured Flask application instance.
    """
    app: Flask = Flask(__name__)
    initialize_loggers(app)

    if os.getenv("ENV") == "testing":
        db_uri = "sqlite+pysqlite:///:memory:"
        logger.info("Using in-memory SQLite database for testing")
    else:
        db_username = os.getenv("POSTGRES_USER")
        db_password = os.getenv("POSTGRES_PASSWORD")
        db_host = os.getenv("POSTGRES_HOST")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        db_name = os.getenv("POSTGRES_DB")
        if not all([db_username, db_password, db_host, db_port, db_name]):
            raise ValueError(
                "Database configuration environment variables are not fully set."
            )
        db_uri = f"postgresql+psycopg2://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"
        logger.info(
            f"Using Database URI: postgresql+psycopg2://{db_username}:XXX@{db_host}:{db_port}/{db_name}"
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret:
        raise ValueError("JWT_SECRET_KEY environment variable is not set.")
    app.config["JWT_SECRET_KEY"] = jwt_secret

    if config_obj:
        app.config.from_object(config_obj)

    register_blueprints(app)
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)

    # Import models so Flask-Migrate can detect them
    with app.app_context():
        from project.models import user_model  # noqa: F401
        from project.models import restaurant_model  # noqa: F401

    cors.init_app(app)
    return app


def initialize_loggers(app):
    """Replaces Flask's default handler with the project's logging configuration."""
    from flask.logging import default_handler

    app.logger.removeHandler(default_handler)
    logging.config.dictConfig(LOGGING_CONFIG)


def register_blueprints(app):
    """
    Registers all API namespaces with Flask-RESTX and mounts the blueprint.

    Add new namespaces here as the project grows.
    """
    from project.blueprints.auth_blueprint import namespace as auth_namespace
    from project.blueprints.restaurant_blueprint import (
        namespace as restaurant_namespace,
    )

    blueprint = Blueprint("api", __name__, url_prefix="/")

    api_extension: Api = Api(
        blueprint,
        title="Abricot Backend API",
        version="1.0",
        description="Documentation of the Abricot Backend API",
        authorizations={
            "Bearer": {
                "type": "apiKey",
                "in": "header",
                "name": "Authorization",
                "description": "Enter: Bearer <JWT token>",
            }
        },
        security="Bearer",
    )

    register_api_handlers(api_extension)
    register_app_handlers(app)

    api_extension.add_namespace(auth_namespace)
    api_extension.add_namespace(restaurant_namespace)

    app.register_blueprint(blueprint)
