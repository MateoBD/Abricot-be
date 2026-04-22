from flask import Flask
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()
cors = CORS()
migrate = Migrate()


def init_extensions(app: Flask) -> None:
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    allowed_origins = app.config.get("ALLOWED_ORIGINS", [])
    if not allowed_origins and not app.config.get("TESTING", False):
        raise RuntimeError("ALLOWED_ORIGINS must define at least one origin.")

    cors.init_app(
        app,
        origins=allowed_origins,
        allow_headers=["Authorization", "Content-Type"],
        supports_credentials=True,
    )

    # Import models so Flask-Migrate can detect schema changes
    with app.app_context():
        from app import models  # noqa: F401
