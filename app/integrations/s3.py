import uuid

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

    def upload_restaurant_photo(self, file_storage, restaurant_id: int) -> str:
        bucket = current_app.config.get("AWS_S3_BUCKET")
        region = current_app.config.get("AWS_REGION")
        use_localstack = bool(current_app.config.get("USE_LOCALSTACK", False))
        localstack_endpoint = current_app.config.get(
            "LOCALSTACK_ENDPOINT", "http://localhost:4566"
        )

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

        if use_localstack:
            return f"{localstack_endpoint}/{bucket}/{key}"
        return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"

    def upload_menu_item_photo(self, file_storage, item_id) -> str:
        bucket = current_app.config.get("AWS_S3_BUCKET")
        region = current_app.config.get("AWS_REGION")
        use_localstack = bool(current_app.config.get("USE_LOCALSTACK", False))
        localstack_endpoint = current_app.config.get(
            "LOCALSTACK_ENDPOINT", "http://localhost:4566"
        )

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

        if use_localstack:
            return f"{localstack_endpoint}/{bucket}/{key}"
        return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def _get_extension(filename: str) -> str:
    if filename and "." in filename:
        return "." + filename.rsplit(".", 1)[-1].lower()
    return ""
