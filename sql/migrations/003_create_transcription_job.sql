USE [audio_pipeline];
GO

IF OBJECT_ID(N'dbo.transcription_job', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.transcription_job
    (
        transcription_job_id BIGINT IDENTITY(1,1) NOT NULL,

        audio_file_id BIGINT NOT NULL,

        engine VARCHAR(50) NOT NULL,

        model_name NVARCHAR(100) NOT NULL,

        requested_language_code VARCHAR(20) NOT NULL
            CONSTRAINT DF_transcription_job_language
            DEFAULT 'auto',

        status VARCHAR(20) NOT NULL
            CONSTRAINT DF_transcription_job_status
            DEFAULT 'PENDING',

        attempt_count SMALLINT NOT NULL
            CONSTRAINT DF_transcription_job_attempt_count
            DEFAULT 0,

        max_attempts SMALLINT NOT NULL
            CONSTRAINT DF_transcription_job_max_attempts
            DEFAULT 3,

        last_error_code VARCHAR(100) NULL,

        last_error_message NVARCHAR(2000) NULL,

        created_at DATETIME2(3) NOT NULL
            CONSTRAINT DF_transcription_job_created_at
            DEFAULT SYSUTCDATETIME(),

        started_at DATETIME2(3) NULL,

        completed_at DATETIME2(3) NULL,

        updated_at DATETIME2(3) NOT NULL
            CONSTRAINT DF_transcription_job_updated_at
            DEFAULT SYSUTCDATETIME(),

        CONSTRAINT PK_transcription_job
            PRIMARY KEY (transcription_job_id),

        CONSTRAINT FK_transcription_job_audio_file
            FOREIGN KEY (audio_file_id)
            REFERENCES dbo.audio_file (audio_file_id),

        CONSTRAINT UQ_transcription_job_request
            UNIQUE (
                audio_file_id,
                engine,
                model_name,
                requested_language_code
            ),

        CONSTRAINT CK_transcription_job_status
            CHECK (
                status IN (
                    'PENDING',
                    'RUNNING',
                    'SUCCESS',
                    'FAILED'
                )
            ),

        CONSTRAINT CK_transcription_job_attempt_count
            CHECK (
                attempt_count >= 0
            ),

        CONSTRAINT CK_transcription_job_max_attempts
            CHECK (
                max_attempts > 0
            )
    );

    CREATE INDEX IX_transcription_job_status
        ON dbo.transcription_job (status);

    CREATE INDEX IX_transcription_job_audio_file
        ON dbo.transcription_job (audio_file_id);
END;
GO