"""Private object storage abstraction.

Default backend writes files to a private directory on disk, outside any web
root, and access is only ever granted through short-lived signed URLs issued by
the API. An S3 backend is wired as an interface: set STORAGE_BACKEND=s3 and the
AWS_* variables to enable it.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
from pathlib import Path

from ..config import settings


class StorageError(RuntimeError):
    pass


class NotConfigured(StorageError):
    pass


_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(name: str) -> str:
    base = os.path.basename(name or "resume")
    base = _SAFE.sub("_", base).strip("._") or "resume"
    return base[:200]


def _local_root() -> Path:
    root = Path(settings.storage_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_bytes(org_id: str, resume_id: str, filename: str, data: bytes) -> str:
    """Persist bytes and return an opaque storage key. Never the raw path."""
    safe = sanitize_filename(filename)
    key = f"{org_id}/resumes/{resume_id}/{safe}"
    if settings.storage_backend == "s3":
        return _s3_save(key, data)
    path = _local_root() / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return key


def read_bytes(key: str) -> bytes:
    if settings.storage_backend == "s3":
        return _s3_read(key)
    path = _local_root() / key
    if not path.exists():
        raise StorageError("File not found")
    return path.read_bytes()


def delete(key: str) -> None:
    if settings.storage_backend == "s3":
        _s3_delete(key)
        return
    path = _local_root() / key
    if path.exists():
        path.unlink()


def local_path(key: str) -> Path:
    return _local_root() / key


# --- S3 interface (unconfigured until credentials are supplied) -----------


def _s3_client():
    if not (settings.aws_s3_bucket and settings.aws_access_key_id and settings.aws_secret_access_key):
        raise NotConfigured(
            "S3 storage selected but AWS_* credentials are not configured. "
            "Set STORAGE_BACKEND=local for local disk storage."
        )
    try:
        import boto3  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise NotConfigured("boto3 is not installed; run `pip install boto3`") from exc
    return boto3.client(
        "s3",
        region_name=settings.aws_region or None,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


def _s3_save(key: str, data: bytes) -> str:  # pragma: no cover - needs AWS
    client = _s3_client()
    client.put_object(
        Bucket=settings.aws_s3_bucket,
        Key=key,
        Body=data,
        ServerSideEncryption="AES256",
    )
    return key


def _s3_read(key: str) -> bytes:  # pragma: no cover - needs AWS
    client = _s3_client()
    obj = client.get_object(Bucket=settings.aws_s3_bucket, Key=key)
    return obj["Body"].read()


def _s3_delete(key: str) -> None:  # pragma: no cover - needs AWS
    client = _s3_client()
    client.delete_object(Bucket=settings.aws_s3_bucket, Key=key)


def presigned_url(key: str) -> str | None:  # pragma: no cover - needs AWS
    if settings.storage_backend != "s3":
        return None
    client = _s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.aws_s3_bucket, "Key": key},
        ExpiresIn=settings.signed_url_ttl_seconds,
    )


def purge_all(root: str | None = None) -> None:
    """Remove all stored files (used by retention jobs / tests)."""
    r = Path(root or settings.storage_dir)
    if r.exists():
        shutil.rmtree(r, ignore_errors=True)
