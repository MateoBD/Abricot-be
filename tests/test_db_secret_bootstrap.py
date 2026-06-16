import json
import os
import sys

import boto3
import pytest

# Mirror the runtime package layout so `common.flask_db` is importable.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LAMBDAS_DIR = os.path.join(_ROOT, "lambdas")
if _LAMBDAS_DIR not in sys.path:
    sys.path.insert(0, _LAMBDAS_DIR)

import common.flask_db as flask_db  # noqa: E402


class _FakeSecretsClient:
    def __init__(self, secret_string):
        self._secret_string = secret_string
        self.calls = []

    def get_secret_value(self, *, SecretId):
        self.calls.append(SecretId)
        return {"SecretString": self._secret_string}


def test_password_is_not_a_required_lambda_env_var():
    # Contract: the rendered Lambda env must NOT carry POSTGRES_PASSWORD; the
    # password comes from Secrets Manager via DB_SECRET_NAME instead.
    assert "POSTGRES_PASSWORD" not in flask_db._REQUIRED_ENV_VARS
    assert "DB_SECRET_NAME" in flask_db._REQUIRED_ENV_VARS


def test_db_password_fetched_from_secrets_manager_and_cached(monkeypatch):
    monkeypatch.setattr(flask_db, "_DB_PASSWORD", None)
    monkeypatch.setenv("DB_SECRET_NAME", "abricot/postgres")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

    fake = _FakeSecretsClient(
        json.dumps({"username": "abricot_app", "password": "s3cr3t-from-secret"})
    )
    monkeypatch.setattr(boto3, "client", lambda service, **kwargs: fake)

    assert flask_db._db_password() == "s3cr3t-from-secret"
    # Cached at module scope: a second call must NOT hit Secrets Manager again.
    assert flask_db._db_password() == "s3cr3t-from-secret"
    assert fake.calls == ["abricot/postgres"]


def test_database_uri_uses_secret_password(monkeypatch):
    monkeypatch.setattr(flask_db, "_DB_PASSWORD", None)
    monkeypatch.setenv("DB_SECRET_NAME", "abricot/postgres")
    monkeypatch.setenv("POSTGRES_USER", "abricot_app")
    monkeypatch.setenv("POSTGRES_HOST", "proxy.internal")
    monkeypatch.setenv("POSTGRES_DB", "abricot")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

    fake = _FakeSecretsClient(json.dumps({"password": "uri-pass"}))
    monkeypatch.setattr(boto3, "client", lambda service, **kwargs: fake)

    uri = flask_db._database_uri()

    assert "uri-pass" in uri
    assert "abricot_app" in uri
    assert "proxy.internal" in uri


def test_db_password_raises_clearly_on_missing_password(monkeypatch):
    monkeypatch.setattr(flask_db, "_DB_PASSWORD", None)
    monkeypatch.setenv("DB_SECRET_NAME", "abricot/postgres")
    fake = _FakeSecretsClient(json.dumps({"username": "no-password-here"}))
    monkeypatch.setattr(boto3, "client", lambda service, **kwargs: fake)

    with pytest.raises(RuntimeError, match="db_secret_missing_password"):
        flask_db._db_password()
