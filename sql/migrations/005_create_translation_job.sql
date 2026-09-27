USE [audio_pipeline];
GO

IF OBJECT_ID(N'dbo.translation_job', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.translation_job
    (
        translation_job_id BIGINT IDENTITY(1,1) NOT NULL,

        transcript_id BIGINT NOT NULL,

        engine VARCHAR(50) NOT NULL,

        model_name NVARCHAR(100) NOT NULL,

        target_language_code VARCHAR(20) NOT NULL,

        status VARCHAR(20) NOT NULL
            CONSTRAINT DF_translation_job_status
            DEFAULT 'PENDING',

        attempt_count SMALLINT NOT NULL
            CONSTRAINT DF_translation_job_attempt_count
            DEFAULT 0,

        max_attempts SMALLINT NOT NULL
            CONSTRAINT DF_translation_job_max_attempts
            DEFAULT 3,

        last_error_code VARCHAR(100) NULL,

        last_error_message NVARCHAR(2000) NULL,

        created_at DATETIME2(3) NOT NULL
            CONSTRAINT DF_translation_job_created_at
            DEFAULT SYSUTCDATETIME(),

        started_at DATETIME2(3) NULL,

        completed_at DATETIME2(3) NULL,

        updated_at DATETIME2(3) NOT NULL
            CONSTRAINT DF_translation_job_updated_at
            DEFAULT SYSUTCDATETIME(),

        CONSTRAINT PK_translation_job
            PRIMARY KEY (translation_job_id),

        CONSTRAINT FK_translation_job_transcript
            FOREIGN KEY (transcript_id)
            REFERENCES dbo.transcript (transcript_id),

        CONSTRAINT UQ_translation_job_request
            UNIQUE (
                transcript_id,
                engine,
                model_name,
                target_language_code
            ),

        CONSTRAINT CK_translation_job_status
            CHECK (
                status IN (
                    'PENDING',
                    'RUNNING',
                    'SUCCESS',
                    'FAILED'
                )
            ),

        CONSTRAINT CK_translation_job_attempt_count
            CHECK (
                attempt_count >= 0
            ),

        CONSTRAINT CK_translation_job_max_attempts
            CHECK (
                max_attempts > 0
            )
    );

    CREATE INDEX IX_translation_job_status
        ON dbo.translation_job (status);

    CREATE INDEX IX_translation_job_transcript
        ON dbo.translation_job (transcript_id);
END;
GO