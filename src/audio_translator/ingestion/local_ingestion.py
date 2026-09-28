import logging
import os
from pathlib import Path

from audio_translator.database.audio_files import (
    register_audio_file,
)
from audio_translator.ingestion.local_source import (
    discover_local_audio_files,
    inspect_local_audio_file,
)
from audio_translator.ingestion.validation import (
    validate_local_audio_file,
)


LOGGER = logging.getLogger(__name__)


def ingest_local_audio_directory(
    root_directory: str | Path | None = None,
) -> list[int]:
    """
    Discover, register and validate all supported local
    audio files.

    Registration and validation are retry-safe.
    """

    if root_directory is None:
        root_directory = os.environ.get(
            "AUDIO_LOCAL_ROOT",
            "/opt/airflow/data/audio_data",
        )

    root_directory = Path(
        root_directory
    )

    discovered_files = (
        discover_local_audio_files(
            root_directory
        )
    )

    LOGGER.info(
        "Discovered %s audio files under %s",
        len(discovered_files),
        root_directory,
    )

    audio_file_ids: list[int] = []

    for file_path in discovered_files:

        source_file = (
            inspect_local_audio_file(
                file_path=file_path,
                root_directory=root_directory,
            )
        )

        audio_file_id = register_audio_file(
            source_system=(
                source_file.source_system
            ),
            source_uri=(
                source_file.source_uri
            ),
            source_version=(
                source_file.source_version
            ),
            original_file_name=(
                source_file.original_file_name
            ),
            content_sha256=(
                source_file.content_sha256
            ),
            file_size_bytes=(
                source_file.file_size_bytes
            ),
            file_extension=(
                source_file.file_extension
            ),
            mime_type=(
                source_file.mime_type
            ),
        )

        validate_local_audio_file(
            audio_file_id=audio_file_id,
            file_path=file_path,
        )

        audio_file_ids.append(
            audio_file_id
        )

        LOGGER.info(
            "Completed local ingestion. "
            "audio_file_id=%s source_uri=%s",
            audio_file_id,
            source_file.source_uri,
        )

    return audio_file_ids