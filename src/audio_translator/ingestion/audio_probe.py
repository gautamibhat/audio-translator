import json
import subprocess
from pathlib import Path

from audio_translator.ingestion.audio_metadata import (
    AudioMetadata,
)


class AudioProbeError(ValueError):
    pass


def probe_audio_file(
    file_path: Path,
) -> AudioMetadata:
    """
    Inspect the first audio stream using ffprobe.
    """

    file_path = (
        file_path
        .expanduser()
        .resolve()
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"Audio file does not exist: {file_path}"
        )

    if not file_path.is_file():
        raise ValueError(
            f"Audio path is not a file: {file_path}"
        )

    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=codec_name,sample_rate,channels",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(file_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise AudioProbeError(
            result.stderr.strip()
            or "ffprobe could not read the audio file"
        )

    try:
        payload = json.loads(
            result.stdout
        )
    except json.JSONDecodeError as exc:
        raise AudioProbeError(
            "ffprobe returned invalid JSON"
        ) from exc

    streams = payload.get(
        "streams",
        []
    )

    if not streams:
        raise AudioProbeError(
            "No audio stream found"
        )

    stream = streams[0]

    try:
        codec = stream["codec_name"]

        sample_rate_hz = int(
            stream["sample_rate"]
        )

        channel_count = int(
            stream["channels"]
        )

        duration_seconds = float(
            payload["format"]["duration"]
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise AudioProbeError(
            "Required audio metadata is missing"
        ) from exc

    duration_ms = round(
        duration_seconds * 1000
    )

    if duration_ms <= 0:
        raise AudioProbeError(
            "Audio duration must be greater than zero"
        )

    if sample_rate_hz <= 0:
        raise AudioProbeError(
            "Audio sample rate must be greater than zero"
        )

    if channel_count <= 0:
        raise AudioProbeError(
            "Audio must contain at least one channel"
        )

    return AudioMetadata(
        duration_ms=duration_ms,
        sample_rate_hz=sample_rate_hz,
        channel_count=channel_count,
        codec=codec,
    )
