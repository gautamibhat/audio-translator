import hashlib
import json
import logging

from airflow.providers.odbc.hooks.odbc import OdbcHook

from audio_translator.common.lifecycle import (
    AudioProcessingStatus,
    ProcessingStage,
    validate_transition,
)


LOGGER = logging.getLogger(__name__)
CONNECTION_ID = "sqlserver_pipeline"


class AudioFileNotFoundError(ValueError):
    pass


def build_source_identifier_hash(
    source_system: str,
    source_uri: str,
    source_version: str | None = None,
) -> str:
    """
    Build a deterministic identifier for one source audio object.

    The same source system, URI and version will always generate
    the same SHA-256 hash.
    """

    normalized_source_system = source_system.strip().upper()
    normalized_source_uri = source_uri.strip()
    normalized_source_version = (
        source_version.strip()
        if source_version is not None
        else None
    )

    if not normalized_source_system:
        raise ValueError("source_system cannot be empty")

    if not normalized_source_uri:
        raise ValueError("source_uri cannot be empty")

    payload = json.dumps(
        {
            "source_system": normalized_source_system,
            "source_uri": normalized_source_uri,
            "source_version": normalized_source_version,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def register_audio_file(
    source_system: str,
    source_uri: str,
    original_file_name: str,
    source_version: str | None = None,
    content_sha256: str | None = None,
    file_size_bytes: int | None = None,
    file_extension: str | None = None,
    mime_type: str | None = None,
) -> int:
    """
    Register one audio source object.

    Registration is idempotent. The same source identity
    returns the existing audio_file_id.
    """

    normalized_source_system = (
        source_system.strip().upper()
    )

    normalized_source_uri = source_uri.strip()

    normalized_source_version = (
        source_version.strip()
        if source_version is not None
        else None
    )

    if normalized_source_system not in {
        "LOCAL",
        "S3",
    }:
        raise ValueError(
            f"Unsupported source system: "
            f"{source_system}"
        )

    if not normalized_source_uri:
        raise ValueError(
            "source_uri cannot be empty"
        )

    if not original_file_name.strip():
        raise ValueError(
            "original_file_name cannot be empty"
        )

    if content_sha256 is not None:
        content_sha256 = (
            content_sha256
            .strip()
            .lower()
        )

        if (
            len(content_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in content_sha256
            )
        ):
            raise ValueError(
                "content_sha256 must be a valid "
                "64-character SHA-256 value"
            )

    if (
        file_size_bytes is not None
        and file_size_bytes < 0
    ):
        raise ValueError(
            "file_size_bytes cannot be negative"
        )

    normalized_file_extension = (
        file_extension
        .strip()
        .lower()
        .lstrip(".")
        if file_extension
        else None
    )

    source_identifier_hash = (
        build_source_identifier_hash(
            source_system=normalized_source_system,
            source_uri=normalized_source_uri,
            source_version=normalized_source_version,
        )
    )

    hook = OdbcHook(
        odbc_conn_id=CONNECTION_ID
    )

    connection = hook.get_conn()
    connection.autocommit = False

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT audio_file_id
            FROM dbo.audio_file
                WITH (UPDLOCK, HOLDLOCK)
            WHERE source_identifier_hash = ?;
            """,
            source_identifier_hash,
        )

        existing_row = cursor.fetchone()

        if existing_row is not None:
            audio_file_id = int(
                existing_row[0]
            )

            connection.commit()

            LOGGER.info(
                "Audio file already registered. "
                "audio_file_id=%s source_uri=%s",
                audio_file_id,
                normalized_source_uri,
            )

            return audio_file_id

        cursor.execute(
            """
            INSERT INTO dbo.audio_file
            (
                source_system,
                source_uri,
                source_version,
                source_identifier_hash,
                original_file_name,
                content_sha256,
                file_size_bytes,
                file_extension,
                mime_type,
                processing_status
            )
            OUTPUT INSERTED.audio_file_id
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                'REGISTERED'
            );
            """,
            normalized_source_system,
            normalized_source_uri,
            normalized_source_version,
            source_identifier_hash,
            original_file_name.strip(),
            content_sha256,
            file_size_bytes,
            normalized_file_extension,
            mime_type,
        )

        inserted_row = cursor.fetchone()

        if inserted_row is None:
            raise RuntimeError(
                "Audio file insert did not return "
                "an audio_file_id"
            )

        audio_file_id = int(
            inserted_row[0]
        )

        cursor.execute(
            """
            INSERT INTO dbo.processing_event
            (
                audio_file_id,
                stage,
                event_type,
                from_status,
                to_status,
                message
            )
            VALUES
            (
                ?,
                'INGESTION',
                'REGISTERED',
                NULL,
                'REGISTERED',
                'Audio file registered'
            );
            """,
            audio_file_id,
        )

        connection.commit()

        LOGGER.info(
            "Audio file registered. "
            "audio_file_id=%s source_uri=%s",
            audio_file_id,
            normalized_source_uri,
        )

        return audio_file_id

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def transition_audio_file_status(
    audio_file_id: int,
    new_status: AudioProcessingStatus,
    stage: ProcessingStage,
    message: str | None = None,
) -> None:
    """
    Move an audio file to another lifecycle state.

    The audio_file update and processing_event insert happen
    in the same database transaction.

    Repeating an already-applied transition is treated as a
    no-op so Airflow retries remain safe.
    """

    hook = OdbcHook(
        odbc_conn_id=CONNECTION_ID
    )

    connection = hook.get_conn()
    connection.autocommit = False

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT processing_status
            FROM dbo.audio_file
                WITH (UPDLOCK, HOLDLOCK)
            WHERE audio_file_id = ?;
            """,
            audio_file_id,
        )

        row = cursor.fetchone()

        if row is None:
            raise AudioFileNotFoundError(
                f"Audio file not found: {audio_file_id}"
            )

        current_status = AudioProcessingStatus(
            row[0]
        )

        if current_status == new_status:
            connection.commit()

            LOGGER.info(
                "Audio file already in requested status. "
                "audio_file_id=%s status=%s",
                audio_file_id,
                new_status.value,
            )

            return

        validate_transition(
            current_status=current_status,
            new_status=new_status,
        )

        cursor.execute(
            """
            UPDATE dbo.audio_file
            SET
                processing_status = ?,
                updated_at = SYSUTCDATETIME()
            WHERE audio_file_id = ?;
            """,
            new_status.value,
            audio_file_id,
        )

        cursor.execute(
            """
            INSERT INTO dbo.processing_event
            (
                audio_file_id,
                stage,
                event_type,
                from_status,
                to_status,
                message
            )
            VALUES
            (
                ?,
                ?,
                'STATUS_CHANGED',
                ?,
                ?,
                ?
            );
            """,
            audio_file_id,
            stage.value,
            current_status.value,
            new_status.value,
            message,
        )

        connection.commit()

        LOGGER.info(
            "Audio status changed. "
            "audio_file_id=%s %s -> %s",
            audio_file_id,
            current_status.value,
            new_status.value,
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def mark_audio_file_validated(
    audio_file_id: int,
    duration_ms: int,
    sample_rate_hz: int,
    channel_count: int,
    codec: str,
    message: str | None = None,
) -> None:
    """
    Persist validated audio metadata and transition the
    audio file to VALIDATED in one transaction.

    Re-running validation for an already VALIDATED file
    is treated as a no-op.
    """

    hook = OdbcHook(
        odbc_conn_id=CONNECTION_ID
    )

    connection = hook.get_conn()
    connection.autocommit = False

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT processing_status
            FROM dbo.audio_file
                WITH (UPDLOCK, HOLDLOCK)
            WHERE audio_file_id = ?;
            """,
            audio_file_id,
        )

        row = cursor.fetchone()

        if row is None:
            raise AudioFileNotFoundError(
                f"Audio file not found: {audio_file_id}"
            )

        current_status = AudioProcessingStatus(
            row[0]
        )

        if (
            current_status
            == AudioProcessingStatus.VALIDATED
        ):
            connection.commit()

            LOGGER.info(
                "Audio file already validated. "
                "audio_file_id=%s",
                audio_file_id,
            )

            return

        validate_transition(
            current_status=current_status,
            new_status=AudioProcessingStatus.VALIDATED,
        )

        cursor.execute(
            """
            UPDATE dbo.audio_file
            SET
                duration_ms = ?,
                sample_rate_hz = ?,
                channel_count = ?,
                codec = ?,
                processing_status = 'VALIDATED',
                updated_at = SYSUTCDATETIME()
            WHERE audio_file_id = ?;
            """,
            duration_ms,
            sample_rate_hz,
            channel_count,
            codec,
            audio_file_id,
        )

        cursor.execute(
            """
            INSERT INTO dbo.processing_event
            (
                audio_file_id,
                stage,
                event_type,
                from_status,
                to_status,
                message
            )
            VALUES
            (
                ?,
                'INGESTION',
                'STATUS_CHANGED',
                ?,
                'VALIDATED',
                ?
            );
            """,
            audio_file_id,
            current_status.value,
            message,
        )

        connection.commit()

        LOGGER.info(
            "Audio file validated. "
            "audio_file_id=%s",
            audio_file_id,
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


