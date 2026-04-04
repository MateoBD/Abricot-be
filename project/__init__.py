# ruff: noqa F401
import logging
import logging.config
import os

from dotenv import load_dotenv
from flask import Blueprint, Flask
from flask_cors import CORS
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

cors = CORS(
    allow_headers=["Authorization", "Content-Type"],
    supports_credentials=True,
    # By default allow all origins. Adjust in production as needed.
    origins=["*"],
)
db = SQLAlchemy()
migrate = Migrate()


def create_app(config_obj=None):
    app: Flask = Flask(__name__)
    initialize_loggers(app)

    if os.getenv("ENV") == "testing":
        db_uri = "sqlite+pysqlite:///:memory:"
        logger.info("Using in-memory SQLite database for testing")
    else:
        db_username = os.getenv("MYSQL_USER")
        db_password = os.getenv("MYSQL_PASSWORD")
        db_host = os.getenv("MYSQL_HOST")
        db_port = os.getenv("MYSQL_PORT", "3306")
        db_name = os.getenv("MYSQL_DATABASE")
        if not all([db_username, db_password, db_host, db_port, db_name]):
            raise ValueError(
                "Database configuration environment variables are not fully set."
            )
        db_uri = (
            f"mysql+pymysql://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"
        )
        logger.info(
            f"Using Database URI: mysql+pymysql://{db_username}:XXX@{db_host}:{db_port}/{db_name}"
        )
    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if config_obj:
        app.config.from_object(config_obj)

    register_blueprints(app)
    db.init_app(app)
    migrate.init_app(app, db)

    # Importar modelos para que Flask-Migrate los detecte
    with app.app_context():
        from project.models import template_model

    initialize_services(app)
    cors.init_app(app)
    return app


def initialize_loggers(app):
    # Set up the loggers
    from flask.logging import default_handler

    app.logger.removeHandler(default_handler)

    logging.config.dictConfig(LOGGING_CONFIG)


def register_blueprints(app):
    # Since the application instance is now created, register each Blueprint
    # with the Flask application instance (app)
    from project.blueprints.template_blueprint import namespace as template_blueprint

    blueprint = Blueprint("api", __name__, url_prefix="/")

    api_extension: Api = Api(
        blueprint,
        title="Template Backend API",
        version="0.1",
        description="Documentation of Template Backend API",
        authorizations={
            "Bearer": {
                "type": "apiKey",
                "in": "header",
                "name": "Authorization",
            }
        },
        decorators=[],
        security="Bearer",
    )

    register_api_handlers(api_extension)
    register_app_handlers(app)

    api_extension.add_namespace(template_blueprint)

    app.register_blueprint(blueprint)


def initialize_services(app):
    """from project.services.email_service import EmailService"""
