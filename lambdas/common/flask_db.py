import os
import ssl
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from flask import Flask
from sqlalchemy.engine import URL

from app.extensions import db

_TLS_SSLMODES = {"require", "verify-ca", "verify-full", "true", "1"}

_REQUIRED_ENV_VARS = (
    "DB_TARGET",
    "POSTGRES_HOST",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
)


def _missing_env() -> list[str]:
    return [name for name in _REQUIRED_ENV_VARS if not os.environ.get(name)]


def _validate_db_env() -> None:
    missing = _missing_env()
    if missing:
        raise RuntimeError(f"missing_db_env:{','.join(missing)}")

    if os.environ.get("DB_TARGET") != "RDS_PROXY":
        raise RuntimeError("invalid_db_target")


def _database_uri() -> str:
    url = URL.create(
        "postgresql+pg8000",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ["POSTGRES_DB"],
    )
    return url.render_as_string(hide_password=False)


def _pg_ssl_context():
    if _pg_sslmode() not in _TLS_SSLMODES:
        return None
    return ssl._create_unverified_context()  # noqa: S323


def _pg_sslmode() -> str:
    return (
        os.environ.get("DB_SSL_MODE")
        or os.environ.get("POSTGRES_SSLMODE")
        or "disable"
    ).strip().lower()


def _engine_options() -> dict[str, Any]:
    ssl_context = _pg_ssl_context()
    if ssl_context is None:
        return {}
    return {"connect_args": {"ssl_context": ssl_context}}


@lru_cache(maxsize=1)
def _lambda_app() -> Flask:
    _validate_db_env()

    app = Flask("abricot_lambda_db_context")
    app.config.update(
        SQLALCHEMY_DATABASE_URI=_database_uri(),
        SQLALCHEMY_ENGINE_OPTIONS=_engine_options(),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    db.init_app(app)
    with app.app_context():
        from app import models  # noqa: F401

    return app


@contextmanager
def backend_app_context():
    """Provide a minimal Flask app context for existing SQLAlchemy services."""
    app = _lambda_app()
    with app.app_context():
        try:
            yield
        except Exception:
            db.session.rollback()
            raise
        finally:
            db.session.remove()
