import hashlib
from io import BytesIO

import pytest

from audio_translator.ingestion.models import SourceAudioFile
from audio_translator.ingestion.s3_materializer import (
    S3MaterializationError,
    _parse_s3_uri,
    materialize_s3_audio_file,
)


class FakeStreamingBody:
    def __init__(self, content: bytes):
        self._buffer = BytesIO(content)
        self.closed = False

    def read(self, amount=-1):
        return self._buffer.read(amount)

    def close(self):
        self.closed = True
        self._buffer.close()


class FakeS3Client:
    def __init__(self, content: bytes):
        self.content = content
        self.calls = []
        self.body = None

    def get_object(self, **kwargs):
        self.calls.append(kwargs)

        self.body = FakeStreamingBody(self.content)

        return {
            "Body": self.body,
            "ContentLength": len(self.content),
        }


def build_source(
    *,
    file_size_bytes: int = 11,
) -> SourceAudioFile:
    return SourceAudioFile(
        source_system="S3",
        source_uri=(
            "s3://audio-translator-dev-test/"
            "incoming/sample.wav"
        ),
        source_version="version-123",
        original_file_name="sample.wav",
        content_sha256=None,
        file_size_bytes=file_size_bytes,
        file_extension=".wav",
        mime_type="audio/x-wav",
    )


def test_parse_s3_uri():
    bucket, key = _parse_s3_uri(
        "s3://my-bucket/incoming/audio.wav"
    )

    assert bucket == "my-bucket"
    assert key == "incoming/audio.wav"


def test_materializes_exact_s3_version():
    content = b"hello audio"

    client = FakeS3Client(content)
    source = build_source(
        file_size_bytes=len(content)
    )

    with materialize_s3_audio_file(
        source,
        s3_client=client,
    ) as materialized:

        assert materialized.local_path.exists()

        assert (
            materialized.local_path.read_bytes()
            == content
        )

        assert (
            materialized.content_sha256
            == hashlib.sha256(content).hexdigest()
        )

        assert materialized.file_size_bytes == len(content)

    assert client.calls == [
        {
            "Bucket": "audio-translator-dev-test",
            "Key": "incoming/sample.wav",
            "VersionId": "version-123",
        }
    ]


def test_temporary_file_is_deleted_after_context():
    content = b"hello audio"

    client = FakeS3Client(content)
    source = build_source(
        file_size_bytes=len(content)
    )

    with materialize_s3_audio_file(
        source,
        s3_client=client,
    ) as materialized:

        local_path = materialized.local_path

        assert local_path.exists()

    assert not local_path.exists()


def test_streaming_body_is_closed():
    content = b"hello audio"

    client = FakeS3Client(content)
    source = build_source(
        file_size_bytes=len(content)
    )

    with materialize_s3_audio_file(
        source,
        s3_client=client,
    ):
        pass

    assert client.body.closed is True


def test_detects_download_size_mismatch():
    content = b"hello audio"

    client = FakeS3Client(content)

    source = build_source(
        file_size_bytes=999
    )

    with pytest.raises(
        S3MaterializationError,
        match="Downloaded size mismatch",
    ):
        with materialize_s3_audio_file(
            source,
            s3_client=client,
        ):
            pass


def test_rejects_non_s3_source():
    source = SourceAudioFile(
        source_system="LOCAL",
        source_uri="local://audio_data/sample.wav",
        source_version="sha256:abc",
        original_file_name="sample.wav",
        content_sha256="abc",
        file_size_bytes=100,
        file_extension=".wav",
        mime_type="audio/x-wav",
    )

    with pytest.raises(
        ValueError,
        match="source_system='S3'",
    ):
        with materialize_s3_audio_file(source):
            pass