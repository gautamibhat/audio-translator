from contextlib import contextmanager

from audio_translator.ingestion.models import SourceAudioFile
from audio_translator.ingestion.s3_ingestion import (
    ingest_s3_audio_prefix,
)
from audio_translator.ingestion.s3_materializer import (
    MaterializedS3AudioFile,
)


def test_ingest_s3_audio_prefix(
    monkeypatch,
    tmp_path,
):
    source = SourceAudioFile(
        source_system="S3",
        source_uri=(
            "s3://audio-translator-dev-test/"
            "incoming/sample.wav"
        ),
        source_version="version-123",
        original_file_name="sample.wav",
        content_sha256=None,
        file_size_bytes=100,
        file_extension=".wav",
        mime_type="audio/x-wav",
    )

    local_file = tmp_path / "sample.wav"
    local_file.write_bytes(b"fake audio")

    materialized = MaterializedS3AudioFile(
        local_path=local_file,
        content_sha256="abc123",
        file_size_bytes=10,
    )

    calls = {}

    def fake_iter_s3_audio_files(
        bucket,
        prefix,
        s3_client=None,
    ):
        calls["discovery"] = {
            "bucket": bucket,
            "prefix": prefix,
        }

        return [source]

    @contextmanager
    def fake_materialize_s3_audio_file(
        source,
        s3_client=None,
    ):
        calls["materialized_source"] = source
        yield materialized

    def fake_register_audio_file(**kwargs):
        calls["registration"] = kwargs
        return 42

    def fake_validate_audio_file(
        audio_file_id,
        file_path,
    ):
        calls["validation"] = {
            "audio_file_id": audio_file_id,
            "file_path": file_path,
        }

    monkeypatch.setattr(
        "audio_translator.ingestion.s3_ingestion."
        "iter_s3_audio_files",
        fake_iter_s3_audio_files,
    )

    monkeypatch.setattr(
        "audio_translator.ingestion.s3_ingestion."
        "materialize_s3_audio_file",
        fake_materialize_s3_audio_file,
    )

    monkeypatch.setattr(
        "audio_translator.ingestion.s3_ingestion."
        "register_audio_file",
        fake_register_audio_file,
    )

    monkeypatch.setattr(
        "audio_translator.ingestion.s3_ingestion."
        "validate_audio_file",
        fake_validate_audio_file,
    )

    result = ingest_s3_audio_prefix(
        bucket="audio-translator-dev-test",
        prefix="incoming/",
    )

    assert result == [42]

    assert calls["discovery"] == {
        "bucket": "audio-translator-dev-test",
        "prefix": "incoming/",
    }

    assert calls["registration"] == {
        "source_system": "S3",
        "source_uri": (
            "s3://audio-translator-dev-test/"
            "incoming/sample.wav"
        ),
        "source_version": "version-123",
        "original_file_name": "sample.wav",
        "content_sha256": "abc123",
        "file_size_bytes": 10,
        "file_extension": ".wav",
        "mime_type": "audio/x-wav",
    }

    assert calls["validation"]["audio_file_id"] == 42
    assert calls["validation"]["file_path"] == local_file


def test_ingest_s3_audio_prefix_requires_bucket(
    monkeypatch,
):
    monkeypatch.delenv(
        "AUDIO_S3_BUCKET",
        raising=False,
    )

    try:
        ingest_s3_audio_prefix()
    except ValueError as exc:
        assert "S3 bucket is required" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for missing S3 bucket"
        )