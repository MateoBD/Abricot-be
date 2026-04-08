import os
import uuid

import boto3


_USE_LOCALSTACK = os.getenv("USE_LOCALSTACK", "false").lower() == "true"
_LOCALSTACK_ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")


class S3Service:
    """Handles file uploads to AWS S3 (or LocalStack in local dev)."""

    _client = None

    @classmethod
    def _get_client(cls):
        if cls._client is None:
            kwargs = {
                "region_name": os.getenv("AWS_REGION"),
            }
            if _USE_LOCALSTACK:
                kwargs["endpoint_url"] = _LOCALSTACK_ENDPOINT
            else:
                kwargs["aws_access_key_id"] = os.getenv("AWS_ACCESS_KEY_ID", "test")
                kwargs["aws_secret_access_key"] = os.getenv(
                    "AWS_SECRET_ACCESS_KEY", "test"
                )
            cls._client = boto3.client("s3", **kwargs)
        return cls._client

    @classmethod
    def upload_restaurant_photo(cls, file_storage, restaurant_id: int) -> str:
        """
        Uploads a photo to S3 under restaurants/<restaurant_id>/<uuid>.<ext>.

        Args:
            file_storage: A Werkzeug FileStorage object.
            restaurant_id: The restaurant's ID (used as folder prefix).

        Returns:
            The public URL of the uploaded object.
        """
        bucket = os.getenv("AWS_S3_BUCKET")
        region = os.getenv("AWS_REGION")

        if not bucket:
            raise ValueError("AWS_S3_BUCKET environment variable is not set.")
        if not region:
            raise ValueError("AWS_REGION environment variable is not set.")

        ext = _get_extension(file_storage.filename)
        key = f"restaurants/{restaurant_id}/{uuid.uuid4().hex}{ext}"

        client = cls._get_client()
        client.upload_fileobj(
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
