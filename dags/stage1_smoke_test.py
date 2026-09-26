from datetime import timedelta
import logging
import pendulum
from airflow.sdk import dag, get_current_context, task
from audio_translator.common.smoke_test import run_smoke_check
from audio_translator.database.connection_check import (
    check_sqlserver_connection,
)
from audio_translator.database.pipeline_runs import (
    mark_pipeline_run_running,
    mark_pipeline_run_success,
)


LOGGER = logging.getLogger(__name__)


@dag(
    dag_id="stage1_smoke_test",
    schedule=None,
    start_date=pendulum.datetime(2026, 9, 1, tz="UTC"),
    catchup=False,
    tags=["audio-translator", "stage1"],
)
def stage1_smoke_test():

    @task(
        retries=2,
        retry_delay=timedelta(seconds=5),
    )
    def start_pipeline_run():
        context = get_current_context()
        ti = context["ti"]

        mark_pipeline_run_running(
            dag_id=ti.dag_id,
            run_id=ti.run_id,
        )

    @task(
        retries=2,
        retry_delay=timedelta(seconds=5),
    )
    def verify_application_code() -> str:
        LOGGER.info(
            "Starting Stage 1 application-code smoke test."
        )

        result = run_smoke_check()

        LOGGER.info(
            "Smoke test result: %s",
            result,
        )

        return result

    @task(
        retries=2,
        retry_delay=timedelta(seconds=5),
    )
    def verify_sqlserver_connection() -> str:
        database_name, login_name = (
            check_sqlserver_connection()
        )

        message = (
            "SQL Server connection successful: "
            f"database={database_name}, "
            f"login={login_name}"
        )

        LOGGER.info(message)

        return message

    @task(
        retries=2,
        retry_delay=timedelta(seconds=5),
    )
    def complete_pipeline_run():
        context = get_current_context()
        ti = context["ti"]

        mark_pipeline_run_success(
            dag_id=ti.dag_id,
            run_id=ti.run_id,
        )

    (
        start_pipeline_run()
        >> verify_application_code()
        >> verify_sqlserver_connection()
        >> complete_pipeline_run()
    )


stage1_smoke_test()