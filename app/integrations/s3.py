import uuid
from urllib.parse import urlparse

import boto3
from flask import current_app


class S3Client:
    _instance: "S3Client | None" = None
    _boto_client = None

    @classmethod
    def get(cls) -> "S3Client":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def _client(self):
        if self._boto_client is None:
            kwargs: dict = {"region_name": current_app.config.get("AWS_REGION")}
            use_localstack = bool(current_app.config.get("USE_LOCALSTACK", False))
            if use_localstack:
                kwargs["endpoint_url"] = current_app.config.get(
                    "LOCALSTACK_ENDPOINT", "http://localhost:4566"
                )
                kwargs["aws_access_key_id"] = current_app.config.get(
                    "AWS_ACCESS_KEY_ID", "test"
                )
                kwargs["aws_secret_access_key"] = current_app.config.get(  # noqa: S105
                    "AWS_SECRET_ACCESS_KEY", "test"
                )
            self._boto_client = boto3.client("s3", **kwargs)
        return self._boto_client

    def generate_presigned_get_url(self, key: str, expires_in: int | None = None) -> str:
        """Return a presigned GET URL for an object key in the photos bucket.

        The bucket is private, so a plain object URL 403s; clients must use a
        short-lived signed URL generated fresh on each read.
        """
        bucket = current_app.config.get("AWS_S3_BUCKET")
        if not bucket:
            raise ValueError("AWS_S3_BUCKET is not configured.")
        if expires_in is None:
            expires_in = int(current_app.config.get("S3_PRESIGNED_EXPIRY", 3600))
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def upload_restaurant_photo(self, file_storage, restaurant_id: int) -> str:
        bucket = current_app.config.get("AWS_S3_BUCKET")
        region = current_app.config.get("AWS_REGION")

        if not bucket:
            raise ValueError("AWS_S3_BUCKET is not configured.")
        if not region:
            raise ValueError("AWS_REGION is not configured.")

        ext = _get_extension(file_storage.filename)
        key = f"restaurants/{restaurant_id}/{uuid.uuid4().hex}{ext}"

        self._client.upload_fileobj(
            file_storage,
            bucket,
            key,
            ExtraArgs={"ContentType": file_storage.content_type},
        )

        # Persist the object KEY (not a URL); the read path signs it on demand.
        return key

    def upload_menu_item_photo(self, file_storage, item_id) -> str:
        bucket = current_app.config.get("AWS_S3_BUCKET")
        region = current_app.config.get("AWS_REGION")

        if not bucket:
            raise ValueError("AWS_S3_BUCKET is not configured.")
        if not region:
            raise ValueError("AWS_REGION is not configured.")

        ext = _get_extension(file_storage.filename)
        key = f"menu-items/{item_id}/{uuid.uuid4().hex}{ext}"

        self._client.upload_fileobj(
            file_storage,
            bucket,
            key,
            ExtraArgs={"ContentType": file_storage.content_type},
        )

        # Persist the object KEY (not a URL); the read path signs it on demand.
        return key


def _get_extension(filename: str) -> str:
    if filename and "." in filename:
        return "." + filename.rsplit(".", 1)[-1].lower()
    return ""


def object_key_from_value(value: str | None) -> str | None:
    """Coerce a stored photo value into an S3 object key.

    New uploads store the bare key. Legacy rows may hold a full object URL;
    derive the key from the URL path so we never sign a key that includes the
    host or bucket. Handles virtual-hosted (``bucket.s3...``) and path-style /
    LocalStack (``host/bucket/key``) URLs.
    """
    if not value:
        return None
    if "://" not in value:
        return value
    path = urlparse(value).path.lstrip("/")
    bucket = current_app.config.get("AWS_S3_BUCKET")
    if bucket and path.startswith(f"{bucket}/"):
        path = path[len(bucket) + 1 :]
    return path or None
