import unittest

from audio_translator.common.lifecycle import (
    AudioProcessingStatus,
    InvalidStatusTransition,
    can_transition,
    validate_transition,
)


class TestAudioProcessingLifecycle(unittest.TestCase):

    def test_registered_can_be_validated(self):
        self.assertTrue(
            can_transition(
                AudioProcessingStatus.REGISTERED,
                AudioProcessingStatus.VALIDATED,
            )
        )

    def test_registered_can_be_rejected(self):
        self.assertTrue(
            can_transition(
                AudioProcessingStatus.REGISTERED,
                AudioProcessingStatus.REJECTED,
            )
        )

    def test_registered_cannot_jump_to_completed(self):
        self.assertFalse(
            can_transition(
                AudioProcessingStatus.REGISTERED,
                AudioProcessingStatus.COMPLETED,
            )
        )

    def test_transcription_lifecycle(self):
        self.assertTrue(
            can_transition(
                AudioProcessingStatus.VALIDATED,
                AudioProcessingStatus.TRANSCRIPTION_PENDING,
            )
        )

        self.assertTrue(
            can_transition(
                AudioProcessingStatus.TRANSCRIPTION_PENDING,
                AudioProcessingStatus.TRANSCRIPTION_RUNNING,
            )
        )

        self.assertTrue(
            can_transition(
                AudioProcessingStatus.TRANSCRIPTION_RUNNING,
                AudioProcessingStatus.TRANSCRIBED,
            )
        )

    def test_translation_lifecycle(self):
        self.assertTrue(
            can_transition(
                AudioProcessingStatus.TRANSCRIBED,
                AudioProcessingStatus.TRANSLATION_PENDING,
            )
        )

        self.assertTrue(
            can_transition(
                AudioProcessingStatus.TRANSLATION_PENDING,
                AudioProcessingStatus.TRANSLATION_RUNNING,
            )
        )

        self.assertTrue(
            can_transition(
                AudioProcessingStatus.TRANSLATION_RUNNING,
                AudioProcessingStatus.COMPLETED,
            )
        )

    def test_processing_can_fail(self):
        self.assertTrue(
            can_transition(
                AudioProcessingStatus.TRANSCRIPTION_RUNNING,
                AudioProcessingStatus.FAILED,
            )
        )

        self.assertTrue(
            can_transition(
                AudioProcessingStatus.TRANSLATION_RUNNING,
                AudioProcessingStatus.FAILED,
            )
        )

    def test_completed_is_terminal(self):
        self.assertFalse(
            can_transition(
                AudioProcessingStatus.COMPLETED,
                AudioProcessingStatus.REGISTERED,
            )
        )

    def test_rejected_is_terminal(self):
        self.assertFalse(
            can_transition(
                AudioProcessingStatus.REJECTED,
                AudioProcessingStatus.VALIDATED,
            )
        )

    def test_failed_is_terminal(self):
        self.assertFalse(
            can_transition(
                AudioProcessingStatus.FAILED,
                AudioProcessingStatus.TRANSCRIPTION_PENDING,
            )
        )

    def test_invalid_transition_raises_exception(self):
        with self.assertRaises(InvalidStatusTransition):
            validate_transition(
                AudioProcessingStatus.REGISTERED,
                AudioProcessingStatus.COMPLETED,
            )


if __name__ == "__main__":
    unittest.main()