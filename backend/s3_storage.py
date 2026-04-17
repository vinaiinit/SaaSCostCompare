"""
S3 storage utility for contract file uploads.

Falls back to local filesystem if S3 is not configured (local dev).
"""
import os
import tempfile
import shutil
from typing import Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


S3_BUCKET = os.getenv("S3_BUCKET")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
S3_PREFIX = os.getenv("S3_PREFIX", "uploads")  # key prefix inside bucket

_s3_client = None


def _get_client():
    """Lazy-init S3 client."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3", region_name=S3_REGION)
    return _s3_client


def is_s3_enabled() -> bool:
    """True when S3 env vars are configured."""
    return bool(S3_BUCKET)


def upload_file(local_path: str, s3_key: str) -> str:
    """
    Upload a single file to S3.
    Returns the full s3:// URI stored in the database.
    """
    client = _get_client()
    full_key = f"{S3_PREFIX}/{s3_key}" if S3_PREFIX else s3_key
    client.upload_file(local_path, S3_BUCKET, full_key)
    return f"s3://{S3_BUCKET}/{full_key}"


def upload_directory(local_dir: str, s3_key_prefix: str) -> str:
    """
    Upload all files in a local directory to S3 under a key prefix.
    Returns the s3:// URI prefix.
    """
    client = _get_client()
    full_prefix = f"{S3_PREFIX}/{s3_key_prefix}" if S3_PREFIX else s3_key_prefix

    for root, _dirs, files in os.walk(local_dir):
        for fname in files:
            local_path = os.path.join(root, fname)
            # Preserve subdirectory structure relative to local_dir
            rel_path = os.path.relpath(local_path, local_dir)
            s3_key = f"{full_prefix}/{rel_path}"
            client.upload_file(local_path, S3_BUCKET, s3_key)

    return f"s3://{S3_BUCKET}/{full_prefix}"


def download_file(s3_key: str, local_path: str) -> str:
    """Download a single file from S3 to a local path."""
    client = _get_client()
    full_key = f"{S3_PREFIX}/{s3_key}" if S3_PREFIX else s3_key
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    client.download_file(S3_BUCKET, full_key, local_path)
    return local_path


def download_directory(s3_key_prefix: str, local_dir: str) -> str:
    """
    Download all files under an S3 prefix to a local directory.
    Returns the local directory path.
    """
    client = _get_client()
    full_prefix = f"{S3_PREFIX}/{s3_key_prefix}" if S3_PREFIX else s3_key_prefix
    os.makedirs(local_dir, exist_ok=True)

    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=full_prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            # Relative path from the prefix
            rel_path = os.path.relpath(key, full_prefix)
            local_path = os.path.join(local_dir, rel_path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            client.download_file(S3_BUCKET, key, local_path)

    return local_dir


def download_to_temp(file_path: str) -> str:
    """
    Given a file_path from the database, return a local path ready for processing.

    - If it's an s3:// URI, download to a temp directory and return that path.
    - If it's a local path, return it as-is.
    """
    if not file_path.startswith("s3://"):
        return file_path

    # Parse s3://bucket/prefix/key
    path_part = file_path[5:]  # strip "s3://"
    bucket = path_part.split("/", 1)[0]
    full_prefix = path_part.split("/", 1)[1] if "/" in path_part else ""

    temp_dir = tempfile.mkdtemp(prefix="saas_extract_")
    client = _get_client()

    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=full_prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            rel_path = os.path.relpath(key, full_prefix)
            local_path = os.path.join(temp_dir, rel_path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            client.download_file(bucket, key, local_path)

    return temp_dir


def generate_presigned_url(s3_key: str, expiry: int = 3600) -> Optional[str]:
    """Generate a presigned download URL. Returns None on error."""
    try:
        client = _get_client()
        full_key = f"{S3_PREFIX}/{s3_key}" if S3_PREFIX else s3_key
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": full_key},
            ExpiresIn=expiry,
        )
        return url
    except ClientError:
        return None


def delete_directory(s3_key_prefix: str) -> None:
    """Delete all objects under an S3 prefix."""
    client = _get_client()
    full_prefix = f"{S3_PREFIX}/{s3_key_prefix}" if S3_PREFIX else s3_key_prefix

    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=full_prefix):
        objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
        if objects:
            client.delete_objects(Bucket=S3_BUCKET, Delete={"Objects": objects})
