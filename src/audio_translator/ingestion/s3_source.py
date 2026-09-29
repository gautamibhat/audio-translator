from __future__ import annotations

import mimetypes
from pathlib import PurePosixPath
from typing import Iterator

import boto3
from botocore.client import BaseClient

from audio_translator.ingestion.models import SourceAudioFile


SUPPORTED_AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".flac",
    ".ogg",
    ".aac",
    ".wma",
    ".webm",
}


class S3SourceError(RuntimeError):
    """Raised when S3 source discovery cannot produce a valid source object."""


def _normalise_prefix(prefix: str) -> str:
    """
    Normalise an S3 prefix so that 'incoming' and 'incoming/'
    behave the same way.
    """
    prefix = prefix.strip("/")

    if not prefix:
        return ""

    return f"{prefix}/"


def _is_supported_audio_key(key: str) -> bool:
    """
    Return True when the S3 object key looks like a supported audio file.
    """
    suffix = PurePosixPath(key).suffix.lower()
    return suffix in SUPPORTED_AUDIO_EXTENSIONS


def _build_source_uri(bucket: str, key: str) -> str:
    return f"s3://{bucket}/{key}"


def iter_s3_audio_files(
    bucket: str,
    prefix: str = "incoming/",
    s3_client: BaseClient | None = None,
) -> Iterator[SourceAudioFile]:
    """
    Discover the latest versions of supported audio files in an S3 prefix.

    Each S3 object version is mapped into the common SourceAudioFile model.

    S3 identity:
        source_system = "S3"
        source_uri     = s3://<bucket>/<key>
        source_version = S3 VersionId

    Only the latest, non-deleted object version is returned.
    """

    if not bucket or not bucket.strip():
        raise ValueError("bucket must not be empty")

    bucket = bucket.strip()
    prefix = _normalise_prefix(prefix)

    client = s3_client or boto3.client("s3")

    paginator = client.get_paginator("list_object_versions")

    try:
        pages = paginator.paginate(
            Bucket=bucket,
            Prefix=prefix,
        )

        for page in pages:
            for version in page.get("Versions", []):
                if not version.get("IsLatest", False):
                    continue

                key = version["Key"]

                # Ignore folder-like placeholder objects.
                if key.endswith("/"):
                    continue

                if not _is_supported_audio_key(key):
                    continue

                version_id = version.get("VersionId")

                if not version_id or version_id == "null":
                    raise S3SourceError(
                        f"S3 object does not have a usable VersionId: "
                        f"s3://{bucket}/{key}"
                    )

                path = PurePosixPath(key)
                extension = path.suffix.lower()
                mime_type, _ = mimetypes.guess_type(path.name)

                yield SourceAudioFile(
                    source_system="S3",
                    source_uri=_build_source_uri(bucket, key),
                    source_version=version_id,
                    original_file_name=path.name,
                    content_sha256=None,
                    file_size_bytes=int(version["Size"]),
                    file_extension=extension,
                    mime_type=mime_type,
                )

    except S3SourceError:
        raise
    except Exception as exc:
        raise S3SourceError(
            f"Failed to discover audio files from "
            f"s3://{bucket}/{prefix}"
        ) from exc