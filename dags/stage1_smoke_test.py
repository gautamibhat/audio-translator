import logging
import pendulum
from airflow.sdk import dag, task
from audio_translator.common.smoke_test import run_smoke_check


LOGGER = logging.getLogger(__name__)


@dag(
    dag_id="stage1_smoke_test",
    schedule=None,
    start_date=pendulum.datetime(2026, 9, 1, tz="UTC"),
    catchup=False,
    tags=["audio-translator", "stage1"],
)
def stage1_smoke_test():

    @task
    def verify_application_code() -> str:
        LOGGER.info("Starting Stage 1 application-code smoke test.")

        result = run_smoke_check()

        LOGGER.info("Smoke test result: %s", result)

        return result

    verify_application_code()


stage1_smoke_test()