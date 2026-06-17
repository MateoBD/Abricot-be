import json
import logging
import os
import ssl
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from flask import Flask
from sqlalchemy.engine import URL

from app.extensions import db

logger = logging.getLogger(__name__)

_TLS_SSLMODES = {"require", "verify-ca", "verify-full", "true", "1"}

# POSTGRES_PASSWORD is intentionally NOT required: the password is fetched at
# cold start from Secrets Manager (DB_SECRET_NAME) and cached at module scope,
# so it never travels as a plaintext Lambda env var.
_REQUIRED_ENV_VARS = (
    "DB_TARGET",
    "POSTGRES_HOST",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "DB_SECRET_NAME",
)

# Module-scope cache: exactly one GetSecretValue per Lambda cold start.
_DB_PASSWORD: str | None = None


def _fetch_secret_password(secret_name: str) -> str:
    """Read the DB password from Secrets Manager. Raises with a clear message."""
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
        return raw  # plain-string secret
    password = data.get("password")
    if not password:
        raise RuntimeError(f"db_secret_missing_password:{secret_name}")
    return password


def _db_password() -> str:
    global _DB_PASSWORD
    if _DB_PASSWORD is None:
        _DB_PASSWORD = _fetch_secret_password(os.environ["DB_SECRET_NAME"])
    return _DB_PASSWORD


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
        password=_db_password(),
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


# Runtime config the domain layer reads from ``current_app.config`` (S3 integration
# and the per-user SNS service). The deployed Lambda env (set in infra/locals.tf,
# plus AWS_REGION injected by the Lambda runtime) must be mirrored into the Flask
# config here, otherwise S3Client/SNS see None and raise (e.g. upload_photo ->
# "AWS_S3_BUCKET is not configured." -> 500). USE_LOCALSTACK/LOCALSTACK_ENDPOINT are
# intentionally excluded: they are unset in Lambda and a string "false" would be
# truthy.
_RUNTIME_CONFIG_ENV_VARS = (
    "AWS_REGION",
    "AWS_S3_BUCKET",
    "S3_PRESIGNED_EXPIRY",
    "EMAIL_NOTIFICATIONS_TOPIC_ARN",
)


def _runtime_config_from_env() -> dict[str, str]:
    return {
        name: os.environ[name]
        for name in _RUNTIME_CONFIG_ENV_VARS
        if os.environ.get(name)
    }


@lru_cache(maxsize=1)
def _lambda_app() -> Flask:
    _validate_db_env()

    app = Flask("abricot_lambda_db_context")
    app.config.update(
        SQLALCHEMY_DATABASE_URI=_database_uri(),
        SQLALCHEMY_ENGINE_OPTIONS=_engine_options(),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        **_runtime_config_from_env(),
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
