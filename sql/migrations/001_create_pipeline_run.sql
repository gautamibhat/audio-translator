USE [audio_pipeline];
GO

IF OBJECT_ID(N'dbo.pipeline_run', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.pipeline_run
    (
        pipeline_run_id BIGINT IDENTITY(1,1) NOT NULL,

        dag_id NVARCHAR(250) NOT NULL,
        run_id NVARCHAR(250) NOT NULL,

        status VARCHAR(20) NOT NULL,

        started_at DATETIME2(3) NOT NULL
            CONSTRAINT DF_pipeline_run_started_at
            DEFAULT SYSUTCDATETIME(),

        completed_at DATETIME2(3) NULL,

        updated_at DATETIME2(3) NOT NULL
            CONSTRAINT DF_pipeline_run_updated_at
            DEFAULT SYSUTCDATETIME(),

        CONSTRAINT PK_pipeline_run
            PRIMARY KEY (pipeline_run_id),

        CONSTRAINT UQ_pipeline_run_dag_run
            UNIQUE (dag_id, run_id),

        CONSTRAINT CK_pipeline_run_status
            CHECK (
                status IN (
                    'RUNNING',
                    'SUCCESS',
                    'FAILED'
                )
            )
    );
END;
GO
