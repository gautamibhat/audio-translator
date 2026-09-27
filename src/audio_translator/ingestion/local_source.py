import hashlib
import mimetypes
from pathlib import Path
from urllib.parse import quote

from audio_translator.ingestion.models import (
    SourceAudioFile,
)


SUPPORTED_AUDIO_EXTENSIONS = frozenset(
    {
        ".wav",
        ".mp3",
        ".m4a",
        ".flac",
        ".ogg",
        ".aac",
        ".wma",
        ".webm",
    }
)


def calculate_content_sha256(
    file_path: Path,
    chunk_size: int = 1024 * 1024,
) -> str:
    """
    Calculate a SHA-256 hash without loading the entire file
    into memory.
    """

    sha256 = hashlib.sha256()

    with file_path.open("rb") as audio_file:
        while chunk := audio_file.read(chunk_size):
            sha256.update(chunk)

    return sha256.hexdigest()


def discover_local_audio_files(
    root_directory: Path,
) -> list[Path]:
    """
    Discover supported audio files recursively.
    """

    root_directory = (
        root_directory
        .expanduser()
        .resolve()
    )

    if not root_directory.exists():
        raise FileNotFoundError(
            f"Audio directory does not exist: "
            f"{root_directory}"
        )

    if not root_directory.is_dir():
        raise NotADirectoryError(
            f"Audio root is not a directory: "
            f"{root_directory}"
        )

    return sorted(
        file_path
        for file_path in root_directory.rglob("*")
        if (
            file_path.is_file()
            and file_path.suffix.lower()
            in SUPPORTED_AUDIO_EXTENSIONS
        )
    )


def inspect_local_audio_file(
    file_path: Path,
    root_directory: Path,
) -> SourceAudioFile:
    """
    Read source-level metadata for one local audio file.

    This does not yet inspect the internal audio stream.
    """

    file_path = (
        file_path
        .expanduser()
        .resolve()
    )

    root_directory = (
        root_directory
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

    try:
        relative_path = file_path.relative_to(
            root_directory
        )
    except ValueError as exc:
        raise ValueError(
            f"Audio file {file_path} is outside "
            f"configured audio root {root_directory}"
        ) from exc

    file_extension = file_path.suffix.lower()

    if file_extension not in SUPPORTED_AUDIO_EXTENSIONS:
        raise ValueError(
            f"Unsupported audio extension: "
            f"{file_extension}"
        )

    content_sha256 = calculate_content_sha256(
        file_path
    )

    file_size_bytes = file_path.stat().st_size

    mime_type, _ = mimetypes.guess_type(
        file_path.name
    )

    encoded_relative_path = quote(
        relative_path.as_posix(),
        safe="/",
    )

    source_uri = (
        f"local://audio_data/"
        f"{encoded_relative_path}"
    )

    source_version = (
        f"sha256:{content_sha256}"
    )

    return SourceAudioFile(
        source_system="LOCAL",
        source_uri=source_uri,
        source_version=source_version,
        original_file_name=file_path.name,
        content_sha256=content_sha256,
        file_size_bytes=file_size_bytes,
        file_extension=file_extension.lstrip("."),
        mime_type=mime_type,
    )