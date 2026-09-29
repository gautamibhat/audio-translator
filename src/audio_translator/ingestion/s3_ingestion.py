from __future__ import annotations

import logging
import os

from botocore.client import BaseClient

from audio_translator.database.audio_files import register_audio_file
from audio_translator.ingestion.s3_materializer import (
    materialize_s3_audio_file,
)
from audio_translator.ingestion.s3_source import (
    iter_s3_audio_files,
)
from audio_translator.ingestion.validation import (
    validate_audio_file,
)


LOGGER = logging.getLogger(__name__)


def ingest_s3_audio_prefix(
    bucket: str | None = None,
    prefix: str | None = None,
    s3_client: BaseClient | None = None,
) -> list[int]:
    """
    Discover, materialize, register and validate audio files from S3.

    When bucket/prefix are not supplied explicitly, configuration is read
    from:

        AUDIO_S3_BUCKET
        AUDIO_S3_PREFIX

    Returns:
        List of audio_file_id values processed during this run.
    """

    resolved_bucket = (
        bucket
        or os.environ.get("AUDIO_S3_BUCKET")
    )

    if not resolved_bucket:
        raise ValueError(
            "S3 bucket is required. Pass bucket=... or set "
            "AUDIO_S3_BUCKET."
        )

    if prefix is None:
        resolved_prefix = os.environ.get(
            "AUDIO_S3_PREFIX",
            "incoming/",
        )
    else:
        resolved_prefix = prefix

    audio_file_ids: list[int] = []

    LOGGER.info(
        "Starting S3 audio ingestion: bucket=%s prefix=%s",
        resolved_bucket,
        resolved_prefix,
    )

    for source in iter_s3_audio_files(
        bucket=resolved_bucket,
        prefix=resolved_prefix,
        s3_client=s3_client,
    ):
        LOGGER.info(
            "Processing S3 audio object: uri=%s version=%s",
            source.source_uri,
            source.source_version,
        )

        with materialize_s3_audio_file(
            source=source,
            s3_client=s3_client,
        ) as materialized:

            audio_file_id = register_audio_file(
                source_system=source.source_system,
                source_uri=source.source_uri,
                source_version=source.source_version,
                original_file_name=source.original_file_name,
                content_sha256=materialized.content_sha256,
                file_size_bytes=materialized.file_size_bytes,
                file_extension=source.file_extension,
                mime_type=source.mime_type,
            )

            validate_audio_file(
                audio_file_id=audio_file_id,
                file_path=materialized.local_path,
            )

            audio_file_ids.append(audio_file_id)

            LOGGER.info(
                "S3 audio ingestion complete: "
                "audio_file_id=%s uri=%s version=%s",
                audio_file_id,
                source.source_uri,
                source.source_version,
            )

    LOGGER.info(
        "S3 ingestion finished. Processed %s audio file(s).",
        len(audio_file_ids),
    )

    return audio_file_ids