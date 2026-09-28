from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AudioMetadata:
    duration_ms: int
    sample_rate_hz: int
    channel_count: int
    codec: str