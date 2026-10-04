from datetime import timedelta
import logging
import os

import pendulum

from airflow.sdk import (
    dag,
    get_current_context,
    task,
)

from audio_translator.database.pipeline_runs import (
    mark_pipeline_run_running,
    mark_pipeline_run_success,
)
from audio_translator.ingestion.local_ingestion import (
    ingest_local_audio_directory,
)
from audio_translator.ingestion.s3_ingestion import (
    ingest_s3_audio_prefix,
)


LOGGER = logging.getLogger(__name__)


@dag(
    dag_id="stage2_audio_ingestion",
    schedule=None,
    start_date=pendulum.datetime(
        2026,
        9,
        1,
        tz="UTC",
    ),
    catchup=False,
    max_active_runs=1,
    tags=[
        "audio-translator",
        "stage2",
        "ingestion",
        "audio",
    ],
)
def stage2_audio_ingestion():

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
        retry_delay=timedelta(seconds=10),
    )
    def ingest_audio_files() -> list[int]:

        LOGGER.info(
            "Starting local audio ingestion."
        )

        source_system = os.environ.get(
            "AUDIO_INGESTION_SOURCE",
            "S3",
        ).upper()

        if source_system == "LOCAL":
            audio_file_ids = ingest_local_audio_directory()
            LOGGER.info(
                "Local ingestion completed. "
                "processed_files=%s "
                "audio_file_ids=%s",
                len(audio_file_ids),
                audio_file_ids,
            )
            return audio_file_ids

        if source_system == "S3":
            audio_file_ids = ingest_s3_audio_prefix()
            LOGGER.info(
                "S3 ingestion completed. "
                "processed_files=%s "
                "audio_file_ids=%s",
                len(audio_file_ids),
                audio_file_ids,
            )
            return audio_file_ids

        raise ValueError(
            f"Unsupported AUDIO_INGESTION_SOURCE: {source_system}. "
            "Expected LOCAL or S3."
        )

    @task(
        retries=2,
        retry_delay=timedelta(seconds=5),
    )
    def complete_pipeline_run(
        audio_file_ids: list[int],
    ):
        context = get_current_context()
        ti = context["ti"]

        LOGGER.info(
            "Completing pipeline run. "
            "processed_files=%s",
            len(audio_file_ids),
        )

        mark_pipeline_run_success(
            dag_id=ti.dag_id,
            run_id=ti.run_id,
        )

    start = start_pipeline_run()

    audio_file_ids = ingest_audio_files()

    complete = complete_pipeline_run(
        audio_file_ids
    )

    start >> audio_file_ids >> complete


stage2_audio_ingestion()