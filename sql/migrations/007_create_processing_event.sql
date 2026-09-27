USE [audio_pipeline];
GO

IF OBJECT_ID(N'dbo.processing_event', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.processing_event
    (
        processing_event_id BIGINT IDENTITY(1,1) NOT NULL,

        audio_file_id BIGINT NOT NULL,

        transcription_job_id BIGINT NULL,

        translation_job_id BIGINT NULL,

        stage VARCHAR(30) NOT NULL,

        event_type VARCHAR(40) NOT NULL,

        from_status VARCHAR(40) NULL,

        to_status VARCHAR(40) NULL,

        message NVARCHAR(2000) NULL,

        details_json NVARCHAR(MAX) NULL,

        created_at DATETIME2(3) NOT NULL
            CONSTRAINT DF_processing_event_created_at
            DEFAULT SYSUTCDATETIME(),

        CONSTRAINT PK_processing_event
            PRIMARY KEY (processing_event_id),

        CONSTRAINT FK_processing_event_audio_file
            FOREIGN KEY (audio_file_id)
            REFERENCES dbo.audio_file (audio_file_id),

        CONSTRAINT FK_processing_event_transcription_job
            FOREIGN KEY (transcription_job_id)
            REFERENCES dbo.transcription_job (
                transcription_job_id
            ),

        CONSTRAINT FK_processing_event_translation_job
            FOREIGN KEY (translation_job_id)
            REFERENCES dbo.translation_job (
                translation_job_id
            ),

        CONSTRAINT CK_processing_event_stage
            CHECK (
                stage IN (
                    'INGESTION',
                    'TRANSCRIPTION',
                    'TRANSLATION'
                )
            ),

        CONSTRAINT CK_processing_event_type
            CHECK (
                event_type IN (
                    'REGISTERED',
                    'STATUS_CHANGED',
                    'ATTEMPT_STARTED',
                    'ATTEMPT_FAILED',
                    'ATTEMPT_SUCCEEDED',
                    'OUTPUT_CREATED'
                )
            ),

        CONSTRAINT CK_processing_event_single_job
            CHECK (
                NOT (
                    transcription_job_id IS NOT NULL
                    AND translation_job_id IS NOT NULL
                )
            ),

        CONSTRAINT CK_processing_event_details_json
            CHECK (
                details_json IS NULL
                OR ISJSON(details_json) = 1
            )
    );

    CREATE INDEX IX_processing_event_audio_created
        ON dbo.processing_event (
            audio_file_id,
            created_at
        );

    CREATE INDEX IX_processing_event_transcription_job
        ON dbo.processing_event (
            transcription_job_id
        );

    CREATE INDEX IX_processing_event_translation_job
        ON dbo.processing_event (
            translation_job_id
        );
END;
GO