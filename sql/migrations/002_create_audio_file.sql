USE [audio_pipeline];
GO

IF OBJECT_ID(N'dbo.audio_file', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.audio_file
    (
        audio_file_id BIGINT IDENTITY(1,1) NOT NULL,

        source_system VARCHAR(20) NOT NULL,

        source_uri NVARCHAR(2048) NOT NULL,

        source_version NVARCHAR(512) NULL,

        source_identifier_hash CHAR(64) NOT NULL,

        original_file_name NVARCHAR(512) NOT NULL,

        content_sha256 CHAR(64) NULL,

        file_size_bytes BIGINT NULL,

        file_extension VARCHAR(20) NULL,

        mime_type VARCHAR(100) NULL,

        duration_ms BIGINT NULL,

        sample_rate_hz INT NULL,

        channel_count SMALLINT NULL,

        codec VARCHAR(100) NULL,

        processing_status VARCHAR(40) NOT NULL
            CONSTRAINT DF_audio_file_processing_status
            DEFAULT 'REGISTERED',

        registered_at DATETIME2(3) NOT NULL
            CONSTRAINT DF_audio_file_registered_at
            DEFAULT SYSUTCDATETIME(),

        updated_at DATETIME2(3) NOT NULL
            CONSTRAINT DF_audio_file_updated_at
            DEFAULT SYSUTCDATETIME(),

        CONSTRAINT PK_audio_file
            PRIMARY KEY (audio_file_id),

        CONSTRAINT UQ_audio_file_source_identifier_hash
            UNIQUE (source_identifier_hash),

        CONSTRAINT CK_audio_file_source_system
            CHECK (
                source_system IN (
                    'LOCAL',
                    'S3'
                )
            ),

        CONSTRAINT CK_audio_file_processing_status
            CHECK (
                processing_status IN (
                    'REGISTERED',
                    'VALIDATED',
                    'REJECTED',
                    'TRANSCRIPTION_PENDING',
                    'TRANSCRIPTION_RUNNING',
                    'TRANSCRIBED',
                    'TRANSLATION_PENDING',
                    'TRANSLATION_RUNNING',
                    'COMPLETED',
                    'FAILED'
                )
            ),

        CONSTRAINT CK_audio_file_size
            CHECK (
                file_size_bytes IS NULL
                OR file_size_bytes >= 0
            ),

        CONSTRAINT CK_audio_file_duration
            CHECK (
                duration_ms IS NULL
                OR duration_ms >= 0
            ),

        CONSTRAINT CK_audio_file_sample_rate
            CHECK (
                sample_rate_hz IS NULL
                OR sample_rate_hz > 0
            ),

        CONSTRAINT CK_audio_file_channel_count
            CHECK (
                channel_count IS NULL
                OR channel_count > 0
            )
    );

    CREATE INDEX IX_audio_file_processing_status
        ON dbo.audio_file (processing_status);
END;
GO