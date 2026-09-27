USE [audio_pipeline];
GO

IF OBJECT_ID(N'dbo.transcript', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.transcript
    (
        transcript_id BIGINT IDENTITY(1,1) NOT NULL,

        transcription_job_id BIGINT NOT NULL,

        language_code VARCHAR(20) NOT NULL,

        transcript_text NVARCHAR(MAX) NOT NULL,

        segment_count INT NULL,

        word_count INT NULL,

        raw_result_json NVARCHAR(MAX) NULL,

        created_at DATETIME2(3) NOT NULL
            CONSTRAINT DF_transcript_created_at
            DEFAULT SYSUTCDATETIME(),

        CONSTRAINT PK_transcript
            PRIMARY KEY (transcript_id),

        CONSTRAINT FK_transcript_transcription_job
            FOREIGN KEY (transcription_job_id)
            REFERENCES dbo.transcription_job (
                transcription_job_id
            ),

        CONSTRAINT UQ_transcript_transcription_job
            UNIQUE (transcription_job_id),

        CONSTRAINT CK_transcript_segment_count
            CHECK (
                segment_count IS NULL
                OR segment_count >= 0
            ),

        CONSTRAINT CK_transcript_word_count
            CHECK (
                word_count IS NULL
                OR word_count >= 0
            ),

        CONSTRAINT CK_transcript_raw_result_json
            CHECK (
                raw_result_json IS NULL
                OR ISJSON(raw_result_json) = 1
            )
    );
END;
GO