import os
from datetime import timedelta


class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    API_VERSION = "1.0.0"
    GIT_SHA = "unknown"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    # Enforce that ALL JWT lookups read exclusively from the Authorization header.
    # This prevents accidental acceptance of tokens from query strings or cookies.
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite+pysqlite:///:memory:"
    JWT_SECRET_KEY = "testing-secret-key-not-for-production"  # noqa: S105
    ALLOWED_ORIGINS = ["*"]


class ProductionConfig(BaseConfig):
    API_VERSION = os.environ.get("API_VERSION", BaseConfig.API_VERSION)
    GIT_SHA = os.environ.get("GIT_SHA", BaseConfig.GIT_SHA)
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "")
    ALLOWED_ORIGINS = [
        o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",")
    ]
    SQLALCHEMY_DATABASE_URI = (
        "postgresql+psycopg2://"
        f"{os.environ.get('POSTGRES_USER', '')}:{os.environ.get('POSTGRES_PASSWORD', '')}"
        f"@{os.environ.get('POSTGRES_HOST', '')}:{os.environ.get('POSTGRES_PORT', '5432')}"
        f"/{os.environ.get('POSTGRES_DB', '')}"
    )

    @classmethod
    def validate(cls) -> None:
        required = [
            "JWT_SECRET_KEY",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_HOST",
            "POSTGRES_DB",
        ]
        missing = [k for k in required if not os.environ.get(k)]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}"
            )


config: dict[str, type] = {
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": ProductionConfig,
}


def get_config_name() -> str:
    return "testing" if os.getenv("ENV") == "testing" else "production"
