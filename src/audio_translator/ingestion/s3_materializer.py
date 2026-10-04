from __future__ import annotations

import hashlib
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Generator
from urllib.parse import urlparse

import boto3
from botocore.client import BaseClient

from audio_translator.ingestion.models import SourceAudioFile


DOWNLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MiB


class S3MaterializationError(RuntimeError):
    """Raised when an S3 audio object cannot be materialized locally."""


@dataclass(frozen=True, slots=True)
class MaterializedS3AudioFile:
    local_path: Path
    content_sha256: str
    file_size_bytes: int


def _parse_s3_uri(source_uri: str) -> tuple[str, str]:
    """
    Parse an S3 URI into bucket and key.

    Example:
        s3://my-bucket/incoming/sample.wav

    Returns:
        ("my-bucket", "incoming/sample.wav")
    """

    parsed = urlparse(source_uri)

    if parsed.scheme != "s3":
        raise ValueError(
            f"Expected an s3:// URI, got: {source_uri}"
        )

    bucket = parsed.netloc
    key = parsed.path.lstrip("/")

    if not bucket:
        raise ValueError(
            f"S3 URI does not contain a bucket: {source_uri}"
        )

    if not key:
        raise ValueError(
            f"S3 URI does not contain an object key: {source_uri}"
        )

    return bucket, key


@contextmanager
def materialize_s3_audio_file(
    source: SourceAudioFile,
    s3_client: BaseClient | None = None,
) -> Generator[MaterializedS3AudioFile, None, None]:
    """
    Download one exact S3 object version to temporary local storage.

    The file is streamed rather than loaded fully into memory.

    SHA-256 is calculated during download.

    The temporary file exists only inside the context manager.
    """

    if source.source_system != "S3":
        raise ValueError(
            "materialize_s3_audio_file requires source_system='S3'"
        )

    if not source.source_version:
        raise ValueError(
            "S3 source must contain a VersionId in source_version"
        )

    bucket, key = _parse_s3_uri(source.source_uri)

    client = s3_client or boto3.client("s3")

    try:
        response = client.get_object(
            Bucket=bucket,
            Key=key,
            VersionId=source.source_version,
        )
    except Exception as exc:
        raise S3MaterializationError(
            f"Failed to download exact S3 object version: "
            f"{source.source_uri} "
            f"(VersionId={source.source_version})"
        ) from exc

    body = response["Body"]

    suffix = source.file_extension or Path(key).suffix

    try:
        with tempfile.TemporaryDirectory(
            prefix="audio-translator-"
        ) as temp_dir:

            local_path = Path(temp_dir) / f"audio{suffix}"

            hasher = hashlib.sha256()
            bytes_written = 0

            try:
                with local_path.open("wb") as output_file:
                    while True:
                        chunk = body.read(DOWNLOAD_CHUNK_SIZE)

                        if not chunk:
                            break

                        output_file.write(chunk)
                        hasher.update(chunk)
                        bytes_written += len(chunk)

            finally:
                body.close()

            if (
                source.file_size_bytes is not None
                and bytes_written != source.file_size_bytes
            ):
                raise S3MaterializationError(
                    f"Downloaded size mismatch for {source.source_uri}. "
                    f"Expected {source.file_size_bytes} bytes, "
                    f"received {bytes_written} bytes."
                )

            yield MaterializedS3AudioFile(
                local_path=local_path,
                content_sha256=hasher.hexdigest(),
                file_size_bytes=bytes_written,
            )

    except S3MaterializationError:
        raise
    except Exception as exc:
        raise S3MaterializationError(
            f"Failed while materializing {source.source_uri}"
        ) from exc