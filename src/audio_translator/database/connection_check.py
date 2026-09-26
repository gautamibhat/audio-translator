import logging

from airflow.providers.odbc.hooks.odbc import OdbcHook


LOGGER = logging.getLogger(__name__)

CONNECTION_ID = "sqlserver_pipeline"


def check_sqlserver_connection() -> tuple[str, str]:
    """
    Verify that the running Airflow task can connect to
    the audio_pipeline SQL Server database.
    """

    hook = OdbcHook(odbc_conn_id=CONNECTION_ID)

    result = hook.get_first(
        """
        SELECT
            DB_NAME() AS database_name,
            SUSER_SNAME() AS login_name;
        """
    )

    database_name, login_name = result

    LOGGER.info(
        "Connected to SQL Server. database=%s login=%s",
        database_name,
        login_name,
    )

    return database_name, login_name
