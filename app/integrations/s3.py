import os
import uuid

import boto3

_USE_LOCALSTACK = os.getenv("USE_LOCALSTACK", "false").lower() == "true"
_LOCALSTACK_ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")


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
            kwargs: dict = {"region_name": os.getenv("AWS_REGION")}
            if _USE_LOCALSTACK:
                kwargs["endpoint_url"] = _LOCALSTACK_ENDPOINT
                kwargs["aws_access_key_id"] = os.getenv("AWS_ACCESS_KEY_ID", "test")
                kwargs["aws_secret_access_key"] = os.getenv(  # noqa: S105
                    "AWS_SECRET_ACCESS_KEY", "test"
                )
            self._boto_client = boto3.client("s3", **kwargs)
        return self._boto_client

    def upload_restaurant_photo(self, file_storage, restaurant_id: int) -> str:
        bucket = os.getenv("AWS_S3_BUCKET")
        region = os.getenv("AWS_REGION")

        if not bucket:
            raise ValueError("AWS_S3_BUCKET environment variable is not set.")
        if not region:
            raise ValueError("AWS_REGION environment variable is not set.")

        ext = _get_extension(file_storage.filename)
        key = f"restaurants/{restaurant_id}/{uuid.uuid4().hex}{ext}"

        self._client.upload_fileobj(
            file_storage,
            bucket,
            key,
            ExtraArgs={"ContentType": file_storage.content_type},
        )

        if _USE_LOCALSTACK:
            return f"{_LOCALSTACK_ENDPOINT}/{bucket}/{key}"
        return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def _get_extension(filename: str) -> str:
    if filename and "." in filename:
        return "." + filename.rsplit(".", 1)[-1].lower()
    return ""
