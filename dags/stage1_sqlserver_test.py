import logging
import pendulum
from airflow.sdk import dag, task
from airflow.providers.odbc.hooks.odbc import OdbcHook


LOGGER = logging.getLogger(__name__)


@dag(
    dag_id="stage1_sqlserver_test",
    schedule=None,
    start_date=pendulum.datetime(2026, 9, 1, tz="UTC"),
    catchup=False,
    tags=["audio-translator", "stage1", "sqlserver"],
)
def stage1_sqlserver_test():

    @task
    def verify_sqlserver_connection():
        hook = OdbcHook(
            odbc_conn_id="sqlserver_pipeline"
        )

        result = hook.get_first("""
            SELECT
                DB_NAME() AS database_name,
                SUSER_SNAME() AS login_name
        """)

        LOGGER.info(
            "Connected to database=%s as login=%s",
            result[0],
            result[1],
        )

        if result[0] != "audio_pipeline":
            raise ValueError(
                f"Unexpected database: {result[0]}"
            )

        if result[1] != "audio_pipeline_app":
            raise ValueError(
                f"Unexpected login: {result[1]}"
            )

        return {
            "database": result[0],
            "login": result[1],
        }

    verify_sqlserver_connection()


stage1_sqlserver_test()
