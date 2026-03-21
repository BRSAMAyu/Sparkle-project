"""Ensure local MinIO buckets exist for acceptance and local development."""

from __future__ import annotations

import os
from typing import Iterable

import boto3
from botocore.exceptions import ClientError


def _bucket_names() -> list[str]:
    names = [
        os.getenv("MINIO_BUCKET", "sparkle-files"),
        os.getenv("MINIO_AVATAR_BUCKET", "sparkle-avatars"),
    ]
    extra = os.getenv("MINIO_EXTRA_BUCKETS", "")
    if extra.strip():
        names.extend(item.strip() for item in extra.split(",") if item.strip())
    # Preserve order while removing duplicates / empties.
    seen: set[str] = set()
    deduped: list[str] = []
    for name in names:
        if not name or name in seen:
            continue
        seen.add(name)
        deduped.append(name)
    return deduped


def _ensure_bucket(s3_client, bucket: str, region: str) -> None:
    try:
        s3_client.head_bucket(Bucket=bucket)
        print(f"[ok] bucket exists: {bucket}")
        return
    except ClientError as exc:
        error_code = str(exc.response.get("Error", {}).get("Code", ""))
        if error_code not in {"404", "NoSuchBucket", "NotFound"}:
            raise

    create_kwargs: dict[str, object] = {"Bucket": bucket}
    if region and region != "us-east-1":
        create_kwargs["CreateBucketConfiguration"] = {
            "LocationConstraint": region,
        }
    s3_client.create_bucket(**create_kwargs)
    print(f"[created] bucket: {bucket}")


def ensure_buckets(buckets: Iterable[str]) -> None:
    endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    region = os.getenv("MINIO_REGION", "")

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region or None,
    )

    for bucket in buckets:
        _ensure_bucket(client, bucket, region)


if __name__ == "__main__":
    ensure_buckets(_bucket_names())
