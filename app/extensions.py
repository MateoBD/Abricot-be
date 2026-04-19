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

    allowed_origins = app.config.get("ALLOWED_ORIGINS", ["*"])
    cors.init_app(
        app,
        origins=allowed_origins,
        allow_headers=["Authorization", "Content-Type"],
        supports_credentials=True,
    )

    # Import models so Flask-Migrate can detect schema changes
    with app.app_context():
        from app.models import restaurant, user  # noqa: F401
