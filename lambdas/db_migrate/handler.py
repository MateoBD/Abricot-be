import json
import logging
import os
import ssl
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_TLS_SSLMODES = {"require", "verify-ca", "verify-full", "true", "1"}

# Password is fetched from Secrets Manager (DB_SECRET_NAME) at cold start and
# cached at module scope; it is never injected as a plaintext env var.
REQUIRED_ENV_VARS = (
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "DB_SECRET_NAME",
)

_DB_PASSWORD: str | None = None


def _fetch_secret_password(secret_name: str) -> str:
    import boto3

    region = os.environ.get("AWS_REGION") or None
    client = boto3.client("secretsmanager", **({"region_name": region} if region else {}))
    try:
        response = client.get_secret_value(SecretId=secret_name)
    except Exception as exc:
        logger.error("db_secret_fetch_failed secret=%s error=%s", secret_name, exc)
        raise RuntimeError(f"db_secret_fetch_failed:{secret_name}") from exc

    raw = response.get("SecretString")
    if not raw:
        raise RuntimeError(f"db_secret_empty:{secret_name}")
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return raw
    password = data.get("password")
    if not password:
        raise RuntimeError(f"db_secret_missing_password:{secret_name}")
    return password


def _db_password() -> str:
    global _DB_PASSWORD
    if _DB_PASSWORD is None:
        _DB_PASSWORD = _fetch_secret_password(os.environ["DB_SECRET_NAME"])
    return _DB_PASSWORD


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Run Flask-Migrate/Alembic migrations from inside the private VPC."""
    try:
        event = event or {}
        missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
        if missing:
            return _json_response(
                500,
                {
                    "ok": False,
                    "error": "missing_environment",
                    "missing": missing,
                },
            )

        action = event.get("action", "upgrade")
        revision = os.environ.get("DB_MIGRATION_REVISION", "head")
        migrations_dir = _migrations_dir()
        logger.info(
            "db_migration_connection_config",
            extra={
                "postgres_host": os.environ.get("POSTGRES_HOST"),
                "postgres_port": os.environ.get("POSTGRES_PORT", "5432"),
                "postgres_sslmode": _pg_sslmode(),
            },
        )

        app = _create_migration_app()
        with app.app_context():
            if action == "validate":
                return _json_response(
                    200,
                    {
                        "ok": True,
                        "operation": "schema validation",
                        "current_revision": _current_alembic_revision(),
                        "schema": _schema_tables(),
                        "db_target": os.environ.get("DB_TARGET", "RDS_PROXY"),
                    },
                )

            if action != "upgrade":
                return _json_response(
                    400,
                    {
                        "ok": False,
                        "error": "unsupported_action",
                        "supported_actions": ["upgrade", "validate"],
                    },
                )

            from flask_migrate import upgrade

            logger.info("db_migration_started", extra={"revision": revision})
            upgrade(directory=str(migrations_dir), revision=revision)
            current_revision = _current_alembic_revision()
            logger.info(
                "db_migration_completed",
                extra={"revision": revision, "current_revision": current_revision},
            )

        return _json_response(
            200,
            {
                "ok": True,
                "operation": "alembic upgrade",
                "target_revision": revision,
                "current_revision": current_revision,
                "db_target": os.environ.get("DB_TARGET", "RDS_PROXY"),
            },
        )
    except ImportError as exc:
        logger.error(
            "db_migration_missing_dependency",
            extra={"error": _safe_error(exc)},
        )
        return _json_response(
            500,
            {
                "ok": False,
                "error": "missing_dependency",
                "message": _safe_error(exc),
                "required_dependencies": [
                    "Flask",
                    "Flask-Migrate",
                    "Alembic",
                    "Flask-SQLAlchemy",
                    "SQLAlchemy",
                    "pg8000",
                    "Flask-Bcrypt",
                    "Flask-Cors",
                    "Flask-JWT-Extended",
                    "uuid6",
                ],
            },
        )
    except Exception as exc:  # noqa: BLE001 - Lambda must return JSON on failures.
        logger.error("db_migration_failed", extra={"error": _safe_error(exc)})
        return _json_response(
            500,
            {
                "ok": False,
                "error": "migration_failed",
                "message": _safe_error(exc),
            },
        )


def _create_migration_app():
    from flask import Flask

    db, migrate = _extensions()

    app = Flask("db_migration_lambda")
    app.config.update(
        SQLALCHEMY_DATABASE_URI=_database_uri(),
        SQLALCHEMY_ENGINE_OPTIONS=_engine_options(),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    db.init_app(app)
    migrate.init_app(app, db, directory=str(_migrations_dir()))

    with app.app_context():
        from app import models  # noqa: F401

    return app


def _database_uri() -> str:
    from sqlalchemy.engine import URL

    url = URL.create(
        "postgresql+pg8000",
        username=os.environ["POSTGRES_USER"],
        password=_db_password(),
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ["POSTGRES_DB"],
    )
    return url.render_as_string(hide_password=False)


def _engine_options() -> dict[str, Any]:
    ssl_context = _pg_ssl_context()
    if ssl_context is None:
        return {}
    return {"connect_args": {"ssl_context": ssl_context}}


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


def _migrations_dir() -> Path:
    configured = os.environ.get("MIGRATIONS_DIR", "migrations")
    path = Path(configured)
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parent / path


def _current_alembic_revision() -> str | None:
    from sqlalchemy import text

    db, _ = _extensions()

    result = db.session.execute(text("select version_num from alembic_version"))
    version = result.scalar()
    db.session.remove()
    return version


def _schema_tables() -> dict[str, Any]:
    from sqlalchemy import text

    db, _ = _extensions()

    rows = db.session.execute(
        text(
            """
            select tablename
            from pg_catalog.pg_tables
            where schemaname = 'public'
            order by tablename
            """
        )
    )
    tables = [row[0] for row in rows]
    db.session.remove()
    return {
        "table_count": len(tables),
        "tables": tables,
        "has_alembic_version": "alembic_version" in tables,
    }


def _json_response(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload, default=str),
    }


def _safe_error(exc: Exception) -> str:
    message = str(exc)
    # Scrub the fetched secret password if it was loaded this cold start.
    if _DB_PASSWORD:
        message = message.replace(_DB_PASSWORD, "***")
    return message


def _extensions():
    from app.extensions import db, migrate

    return db, migrate
