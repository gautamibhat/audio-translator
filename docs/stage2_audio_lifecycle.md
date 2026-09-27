# Stage 2 — Audio Processing Lifecycle

## Purpose

Stage 2 defines how an audio file moves through the audio processing
pipeline before implementing the actual ingestion, transcription or
translation logic.

The database will keep track of:

- audio files
- transcription jobs
- transcripts
- translation jobs
- translations
- processing events
- retries
- failures
- timestamps and audit history

## Audio lifecycle

REGISTERED
→ VALIDATED
→ TRANSCRIPTION_PENDING
→ TRANSCRIPTION_RUNNING
→ TRANSCRIBED
→ TRANSLATION_PENDING
→ TRANSLATION_RUNNING
→ COMPLETED

Possible failure states:

REJECTED
FAILED

## Core entities

### audio_file

Represents one audio asset known to the system.

It stores source information, technical audio metadata and the
high-level processing status.

### transcription_job

Represents a logical request to transcribe an audio file.

Retries update the same logical job rather than creating duplicate
transcription jobs.

### transcript

Stores the successful output of a transcription job.

### translation_job

Represents a logical request to translate a transcript into a target
language.

Retries update the same logical job.

### translation

Stores the successful translated text.

### processing_event

Stores important lifecycle events and status transitions so that the
history of an audio file can be inspected later.

## Design principles

The database model should support:

- idempotent processing
- retries
- failure investigation
- auditability
- UTC timestamps
- multiple audio files
- multiple translations
- future S3 ingestion
- future transcription engines
- future translation engines

Stage 2 intentionally does not implement the actual audio processing.