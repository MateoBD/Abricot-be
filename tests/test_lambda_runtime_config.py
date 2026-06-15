import os
import sys

# `common` must be importable, mirroring the runtime layout from package_lambdas.sh.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LAMBDAS_DIR = os.path.join(_ROOT, "lambdas")
if _LAMBDAS_DIR not in sys.path:
    sys.path.insert(0, _LAMBDAS_DIR)

import common.flask_db as flask_db  # noqa: E402

_KEYS = ("AWS_REGION", "AWS_S3_BUCKET", "S3_PRESIGNED_EXPIRY", "SNS_USER_TOPIC_PREFIX")


def test_runtime_config_mirrors_aws_env_into_flask_config(monkeypatch):
    # Regression: the Lambda Flask app must carry AWS_S3_BUCKET/AWS_REGION so
    # S3Client (and the SNS service) don't see None. Missing AWS_S3_BUCKET made
    # upload_photo raise "AWS_S3_BUCKET is not configured." -> 500.
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_S3_BUCKET", "abricot-123-images")
    monkeypatch.setenv("SNS_USER_TOPIC_PREFIX", "abricot-user")
    monkeypatch.delenv("S3_PRESIGNED_EXPIRY", raising=False)

    config = flask_db._runtime_config_from_env()

    assert config["AWS_S3_BUCKET"] == "abricot-123-images"
    assert config["AWS_REGION"] == "us-east-1"
    assert config["SNS_USER_TOPIC_PREFIX"] == "abricot-user"
    # Unset optional keys are omitted (S3Client falls back to its own default).
    assert "S3_PRESIGNED_EXPIRY" not in config


def test_runtime_config_omits_unset_keys(monkeypatch):
    for key in _KEYS:
        monkeypatch.delenv(key, raising=False)

    assert flask_db._runtime_config_from_env() == {}
