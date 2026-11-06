"""Storage abstraction (local filesystem + S3-compatible object storage).

Large media (uploaded audio/video/PDF/images) belongs in blob storage, not the
relational DB. The rest of the app only ever talks to the ``Storage`` interface,
so switching between local disk and S3/MinIO is a config change
(``STORAGE_BACKEND=local|s3``).
"""

from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod

from app.config import settings


class Storage(ABC):
    @abstractmethod
    def save_bytes(self, data: bytes, filename: str, subdir: str = "") -> str:
        """Persist bytes and return an identifier/URI that ``local_path`` or a
        client can later resolve."""

    @abstractmethod
    def local_path(self, key: str) -> str:
        """Return a real local filesystem path for ``key`` (downloading from
        object storage into a temp file if necessary). Used by media/OCR tools
        that need a file on disk."""


class LocalStorage(Storage):
    def __init__(self, base_dir: str) -> None:
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def save_bytes(self, data: bytes, filename: str, subdir: str = "") -> str:
        safe = f"{uuid.uuid4().hex}_{os.path.basename(filename)}"
        target_dir = os.path.join(self.base_dir, subdir) if subdir else self.base_dir
        os.makedirs(target_dir, exist_ok=True)
        path = os.path.join(target_dir, safe)
        with open(path, "wb") as f:
            f.write(data)
        return path  # for local storage the key IS the path

    def local_path(self, key: str) -> str:
        return key


class S3Storage(Storage):
    """S3-compatible object storage (AWS S3, MinIO, R2, ...). Requires boto3 and
    ``S3_BUCKET`` / optional ``S3_ENDPOINT_URL``."""

    def __init__(self, bucket: str, endpoint_url: str = "") -> None:
        import boto3  # type: ignore

        self.bucket = bucket
        self._tmp_dir = os.path.join(settings.storage_dir, "_s3cache")
        os.makedirs(self._tmp_dir, exist_ok=True)
        self._client = boto3.client(
            "s3", endpoint_url=endpoint_url or None
        )

    def save_bytes(self, data: bytes, filename: str, subdir: str = "") -> str:
        key = f"{subdir + '/' if subdir else ''}{uuid.uuid4().hex}_{os.path.basename(filename)}"
        self._client.put_object(Bucket=self.bucket, Key=key, Body=data)
        return f"s3://{self.bucket}/{key}"

    def local_path(self, key: str) -> str:
        # download s3://bucket/key into the temp cache and return the path
        assert key.startswith("s3://")
        _, _, rest = key.partition("s3://")
        bucket, _, object_key = rest.partition("/")
        dest = os.path.join(self._tmp_dir, os.path.basename(object_key))
        self._client.download_file(bucket, object_key, dest)
        return dest


def get_storage() -> Storage:
    if settings.storage_backend == "s3" and settings.s3_bucket:
        try:
            return S3Storage(settings.s3_bucket, settings.s3_endpoint_url)
        except Exception:
            pass  # fall back to local if boto3/creds missing
    return LocalStorage(settings.storage_dir)


storage = get_storage()
