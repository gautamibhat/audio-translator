from enum import Enum


class AudioProcessingStatus(str, Enum):
    REGISTERED = "REGISTERED"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    TRANSCRIPTION_PENDING = "TRANSCRIPTION_PENDING"
    TRANSCRIPTION_RUNNING = "TRANSCRIPTION_RUNNING"
    TRANSCRIBED = "TRANSCRIBED"
    TRANSLATION_PENDING = "TRANSLATION_PENDING"
    TRANSLATION_RUNNING = "TRANSLATION_RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ProcessingStage(str, Enum):
    INGESTION = "INGESTION"
    TRANSCRIPTION = "TRANSCRIPTION"
    TRANSLATION = "TRANSLATION"
    

ALLOWED_TRANSITIONS = {
    AudioProcessingStatus.REGISTERED: {
        AudioProcessingStatus.VALIDATED,
        AudioProcessingStatus.REJECTED,
    },

    AudioProcessingStatus.VALIDATED: {
        AudioProcessingStatus.TRANSCRIPTION_PENDING,
        AudioProcessingStatus.FAILED,
    },

    AudioProcessingStatus.TRANSCRIPTION_PENDING: {
        AudioProcessingStatus.TRANSCRIPTION_RUNNING,
        AudioProcessingStatus.FAILED,
    },

    AudioProcessingStatus.TRANSCRIPTION_RUNNING: {
        AudioProcessingStatus.TRANSCRIBED,
        AudioProcessingStatus.FAILED,
    },

    AudioProcessingStatus.TRANSCRIBED: {
        AudioProcessingStatus.TRANSLATION_PENDING,
    },

    AudioProcessingStatus.TRANSLATION_PENDING: {
        AudioProcessingStatus.TRANSLATION_RUNNING,
        AudioProcessingStatus.FAILED,
    },

    AudioProcessingStatus.TRANSLATION_RUNNING: {
        AudioProcessingStatus.COMPLETED,
        AudioProcessingStatus.FAILED,
    },

    AudioProcessingStatus.REJECTED: set(),
    AudioProcessingStatus.COMPLETED: set(),
    AudioProcessingStatus.FAILED: set(),
}


class InvalidStatusTransition(ValueError):
    pass


def can_transition(
    current_status: AudioProcessingStatus,
    new_status: AudioProcessingStatus,
) -> bool:
    return new_status in ALLOWED_TRANSITIONS[current_status]


def validate_transition(
    current_status: AudioProcessingStatus,
    new_status: AudioProcessingStatus,
) -> None:
    if can_transition(current_status, new_status):
        return

    raise InvalidStatusTransition(
        f"Invalid audio status transition: "
        f"{current_status.value} -> {new_status.value}"
    )