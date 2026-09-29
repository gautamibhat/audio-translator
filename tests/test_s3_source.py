from __future__ import annotations

import pytest

from audio_translator.ingestion.s3_source import (
    S3SourceError,
    iter_s3_audio_files,
)


class FakePaginator:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def paginate(self, **kwargs):
        self.calls.append(kwargs)
        return iter(self.pages)


class FakeS3Client:
    def __init__(self, pages):
        self.paginator = FakePaginator(pages)
        self.requested_paginator = None

    def get_paginator(self, name):
        self.requested_paginator = name
        return self.paginator


def test_iter_s3_audio_files_maps_latest_audio_versions():
    client = FakeS3Client(
        pages=[
            {
                "Versions": [
                    {
                        "Key": "incoming/sample.wav",
                        "VersionId": "version-123",
                        "IsLatest": True,
                        "Size": 4096,
                    },
                    {
                        "Key": "incoming/sample.wav",
                        "VersionId": "version-old",
                        "IsLatest": False,
                        "Size": 2048,
                    },
                    {
                        "Key": "incoming/notes.txt",
                        "VersionId": "version-text",
                        "IsLatest": True,
                        "Size": 100,
                    },
                    {
                        "Key": "incoming/",
                        "VersionId": "folder-version",
                        "IsLatest": True,
                        "Size": 0,
                    },
                ]
            }
        ]
    )

    files = list(
        iter_s3_audio_files(
            bucket="audio-translator-dev-test",
            prefix="incoming/",
            s3_client=client,
        )
    )

    assert len(files) == 1

    audio = files[0]

    assert audio.source_system == "S3"
    assert (
        audio.source_uri
        == "s3://audio-translator-dev-test/incoming/sample.wav"
    )
    assert audio.source_version == "version-123"
    assert audio.original_file_name == "sample.wav"
    assert audio.file_size_bytes == 4096
    assert audio.file_extension == ".wav"
    assert audio.content_sha256 is None

    assert client.requested_paginator == "list_object_versions"
    assert client.paginator.calls == [
        {
            "Bucket": "audio-translator-dev-test",
            "Prefix": "incoming/",
        }
    ]


def test_iter_s3_audio_files_handles_multiple_pages():
    client = FakeS3Client(
        pages=[
            {
                "Versions": [
                    {
                        "Key": "incoming/one.mp3",
                        "VersionId": "v1",
                        "IsLatest": True,
                        "Size": 1000,
                    }
                ]
            },
            {
                "Versions": [
                    {
                        "Key": "incoming/two.flac",
                        "VersionId": "v2",
                        "IsLatest": True,
                        "Size": 2000,
                    }
                ]
            },
        ]
    )

    files = list(
        iter_s3_audio_files(
            bucket="audio-translator-dev-test",
            prefix="incoming/",
            s3_client=client,
        )
    )

    assert len(files) == 2

    assert files[0].source_version == "v1"
    assert files[1].source_version == "v2"

    assert files[0].original_file_name == "one.mp3"
    assert files[1].original_file_name == "two.flac"


def test_iter_s3_audio_files_filters_unsupported_extensions():
    client = FakeS3Client(
        pages=[
            {
                "Versions": [
                    {
                        "Key": "incoming/audio.wav",
                        "VersionId": "audio-version",
                        "IsLatest": True,
                        "Size": 1234,
                    },
                    {
                        "Key": "incoming/document.pdf",
                        "VersionId": "pdf-version",
                        "IsLatest": True,
                        "Size": 500,
                    },
                    {
                        "Key": "incoming/image.png",
                        "VersionId": "image-version",
                        "IsLatest": True,
                        "Size": 700,
                    },
                ]
            }
        ]
    )

    files = list(
        iter_s3_audio_files(
            bucket="audio-translator-dev-test",
            s3_client=client,
        )
    )

    assert len(files) == 1
    assert files[0].original_file_name == "audio.wav"


def test_iter_s3_audio_files_ignores_non_latest_versions():
    client = FakeS3Client(
        pages=[
            {
                "Versions": [
                    {
                        "Key": "incoming/sample.wav",
                        "VersionId": "old-version",
                        "IsLatest": False,
                        "Size": 1000,
                    },
                    {
                        "Key": "incoming/sample.wav",
                        "VersionId": "new-version",
                        "IsLatest": True,
                        "Size": 1200,
                    },
                ]
            }
        ]
    )

    files = list(
        iter_s3_audio_files(
            bucket="audio-translator-dev-test",
            s3_client=client,
        )
    )

    assert len(files) == 1
    assert files[0].source_version == "new-version"
    assert files[0].file_size_bytes == 1200


def test_iter_s3_audio_files_normalises_prefix():
    client = FakeS3Client(pages=[{"Versions": []}])

    list(
        iter_s3_audio_files(
            bucket="audio-translator-dev-test",
            prefix="/incoming",
            s3_client=client,
        )
    )

    assert client.paginator.calls == [
        {
            "Bucket": "audio-translator-dev-test",
            "Prefix": "incoming/",
        }
    ]


def test_iter_s3_audio_files_accepts_uppercase_extension():
    client = FakeS3Client(
        pages=[
            {
                "Versions": [
                    {
                        "Key": "incoming/RECORDING.WAV",
                        "VersionId": "version-uppercase",
                        "IsLatest": True,
                        "Size": 5000,
                    }
                ]
            }
        ]
    )

    files = list(
        iter_s3_audio_files(
            bucket="audio-translator-dev-test",
            s3_client=client,
        )
    )

    assert len(files) == 1
    assert files[0].original_file_name == "RECORDING.WAV"
    assert files[0].file_extension == ".wav"


def test_iter_s3_audio_files_rejects_missing_version_id():
    client = FakeS3Client(
        pages=[
            {
                "Versions": [
                    {
                        "Key": "incoming/sample.wav",
                        "VersionId": None,
                        "IsLatest": True,
                        "Size": 1000,
                    }
                ]
            }
        ]
    )

    with pytest.raises(
        S3SourceError,
        match="does not have a usable VersionId",
    ):
        list(
            iter_s3_audio_files(
                bucket="audio-translator-dev-test",
                s3_client=client,
            )
        )


def test_iter_s3_audio_files_rejects_empty_bucket():
    client = FakeS3Client(pages=[])

    with pytest.raises(
        ValueError,
        match="bucket must not be empty",
    ):
        list(
            iter_s3_audio_files(
                bucket="",
                s3_client=client,
            )
        )