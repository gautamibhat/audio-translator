IF EXISTS (
    SELECT 1
    FROM sys.sql_logins
    WHERE name = N'audio_pipeline_app'
)
BEGIN
    ALTER LOGIN [audio_pipeline_app]
        WITH PASSWORD = N'$(APP_DB_PASSWORD)';
END
ELSE
BEGIN
    CREATE LOGIN [audio_pipeline_app]
        WITH PASSWORD = N'$(APP_DB_PASSWORD)',
        CHECK_POLICY = ON;
END;
GO

USE [audio_pipeline];
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.database_principals
    WHERE name = N'audio_pipeline_app'
)
BEGIN
    CREATE USER [audio_pipeline_app]
        FOR LOGIN [audio_pipeline_app];
END;
GO

GRANT SELECT, INSERT, UPDATE
ON SCHEMA::dbo
TO [audio_pipeline_app];
GO