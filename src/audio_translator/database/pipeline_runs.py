import logging
from airflow.providers.odbc.hooks.odbc import OdbcHook


LOGGER = logging.getLogger(__name__)
CONNECTION_ID = "sqlserver_pipeline"


def mark_pipeline_run_running(dag_id: str, run_id: str) -> None:
    """
    Insert one row for a new Airflow DAG run.

    If the same DAG run is retried/re-run, update the existing
    row instead of creating a duplicate.
    """

    hook = OdbcHook(odbc_conn_id=CONNECTION_ID)

    sql = """
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRANSACTION;

    UPDATE dbo.pipeline_run WITH (UPDLOCK, HOLDLOCK)
    SET
        status = 'RUNNING',
        completed_at = NULL,
        updated_at = SYSUTCDATETIME()
    WHERE dag_id = ?
      AND run_id = ?;

    IF @@ROWCOUNT = 0
    BEGIN
        INSERT INTO dbo.pipeline_run
        (
            dag_id,
            run_id,
            status
        )
        VALUES
        (
            ?,
            ?,
            'RUNNING'
        );
    END;

    COMMIT TRANSACTION;
    """

    hook.run(
        sql,
        parameters=(dag_id, run_id, dag_id, run_id),
        autocommit=True,
    )

    LOGGER.info(
        "Pipeline run marked RUNNING. dag_id=%s run_id=%s",
        dag_id,
        run_id,
    )


def mark_pipeline_run_success(dag_id: str, run_id: str) -> None:
    """Mark an existing pipeline run as successfully completed."""

    hook = OdbcHook(odbc_conn_id=CONNECTION_ID)

    sql = """
    UPDATE dbo.pipeline_run
    SET
        status = 'SUCCESS',
        completed_at = SYSUTCDATETIME(),
        updated_at = SYSUTCDATETIME()
    WHERE dag_id = ?
      AND run_id = ?;
    """

    hook.run(
        sql,
        parameters=(dag_id, run_id),
        autocommit=True,
    )

    LOGGER.info(
        "Pipeline run marked SUCCESS. dag_id=%s run_id=%s",
        dag_id,
        run_id,
    )
