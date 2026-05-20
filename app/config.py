import os
from datetime import timedelta


def parse_allowed_origins() -> list[str]:
    """Comma-separated ALLOWED_ORIGINS from the environment (used after load_dotenv)."""
    return [
        o.strip()
        for o in os.environ.get("ALLOWED_ORIGINS", "").split(",")
        if o.strip()
    ]


class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    API_VERSION = "1.0.0"
    GIT_SHA = "unknown"
    PORT = 5000
    TIMEZONE = "UTC"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    # Enforce that ALL JWT lookups read exclusively from the Authorization header.
    # This prevents accidental acceptance of tokens from query strings or cookies.
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"
    USE_LOCALSTACK = False
    LOCALSTACK_ENDPOINT = "http://localhost:4566"
    AWS_REGION = ""
    AWS_S3_BUCKET = ""
    AWS_ACCESS_KEY_ID = ""
    AWS_SECRET_ACCESS_KEY = ""


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite+pysqlite:///:memory:"
    JWT_SECRET_KEY = "testing-secret-key-not-for-production"  # noqa: S105
    ALLOWED_ORIGINS = ["*"]
    AWS_REGION = "us-east-1"
    AWS_S3_BUCKET = "abricot-test-bucket"
    AWS_ACCESS_KEY_ID = "test"
    AWS_SECRET_ACCESS_KEY = "test"  # noqa: S105


class ProductionConfig(BaseConfig):
    API_VERSION = os.environ.get("API_VERSION", BaseConfig.API_VERSION)
    GIT_SHA = os.environ.get("GIT_SHA", BaseConfig.GIT_SHA)
    PORT = int(os.environ.get("PORT", str(BaseConfig.PORT)))
    TIMEZONE = os.environ.get("TIMEZONE", BaseConfig.TIMEZONE)
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "")
    USE_LOCALSTACK = os.environ.get("USE_LOCALSTACK", "false").lower() == "true"
    LOCALSTACK_ENDPOINT = os.environ.get(
        "LOCALSTACK_ENDPOINT", BaseConfig.LOCALSTACK_ENDPOINT
    )
    AWS_REGION = os.environ.get("AWS_REGION", "")
    AWS_S3_BUCKET = os.environ.get("AWS_S3_BUCKET", "")
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    ALLOWED_ORIGINS = parse_allowed_origins()
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
            "ALLOWED_ORIGINS",
            "AWS_REGION",
            "AWS_S3_BUCKET",
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
        origins = parse_allowed_origins()
        if "*" in origins:
            raise EnvironmentError(
                "ALLOWED_ORIGINS must list explicit origins in production; '*' is not allowed."
            )


config: dict[str, type] = {
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": ProductionConfig,
}


def get_config_name() -> str:
    return "testing" if os.getenv("ENV") == "testing" else "production"
