import logging


LOGGER = logging.getLogger(__name__)


def run_smoke_check() -> str:
    """
    Verify that Airflow can import and execute code
    from the audio_translator application package.
    """

    message = "Stage 1 smoke check passed: audio_translator package is working."

    LOGGER.info(message)

    return message