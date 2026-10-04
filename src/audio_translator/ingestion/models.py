from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceAudioFile:
    source_system: str
    source_uri: str
    source_version: str
    original_file_name: str
    content_sha256: str
    file_size_bytes: int
    file_extension: str
    mime_type: str | None