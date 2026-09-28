import logging
from pathlib import Path

from audio_translator.common.lifecycle import (
    AudioProcessingStatus,
    ProcessingStage,
)
from audio_translator.database.audio_files import (
    mark_audio_file_validated,
    transition_audio_file_status,
)
from audio_translator.ingestion.audio_probe import (
    AudioProbeError,
    probe_audio_file,
)


LOGGER = logging.getLogger(__name__)


def validate_local_audio_file(
    audio_file_id: int,
    file_path: Path,
) -> None:

    try:
        metadata = probe_audio_file(
            file_path
        )

    except AudioProbeError as exc:

        transition_audio_file_status(
            audio_file_id=audio_file_id,
            new_status=(
                AudioProcessingStatus.REJECTED
            ),
            stage=ProcessingStage.INGESTION,
            message=str(exc),
        )

        LOGGER.warning(
            "Audio file rejected. "
            "audio_file_id=%s reason=%s",
            audio_file_id,
            exc,
        )

        return

    mark_audio_file_validated(
        audio_file_id=audio_file_id,
        duration_ms=metadata.duration_ms,
        sample_rate_hz=metadata.sample_rate_hz,
        channel_count=metadata.channel_count,
        codec=metadata.codec,
        message="Audio stream validated successfully",
    )

