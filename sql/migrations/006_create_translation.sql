USE [audio_pipeline];
GO

IF OBJECT_ID(N'dbo.translation', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.translation
    (
        translation_id BIGINT IDENTITY(1,1) NOT NULL,

        translation_job_id BIGINT NOT NULL,

        translated_text NVARCHAR(MAX) NOT NULL,

        created_at DATETIME2(3) NOT NULL
            CONSTRAINT DF_translation_created_at
            DEFAULT SYSUTCDATETIME(),

        CONSTRAINT PK_translation
            PRIMARY KEY (translation_id),

        CONSTRAINT FK_translation_translation_job
            FOREIGN KEY (translation_job_id)
            REFERENCES dbo.translation_job (
                translation_job_id
            ),

        CONSTRAINT UQ_translation_translation_job
            UNIQUE (translation_job_id)
    );
END;
GO