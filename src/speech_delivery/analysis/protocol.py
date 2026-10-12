"""The seam between the API and the analysis pipeline.

The API imports this module and nothing heavier, so it can be tested with a fake analyzer and
the real pipeline can change without touching it.
"""

from pathlib import Path
from typing import Protocol

from ..contract import AnalyzeOptions, ErrorCode, Report, Stage


class AnalysisError(Exception):
    """A failure the participant can act on. `code` is what the API reports in a FailedEvent."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ProgressSink(Protocol):
    def __call__(self, stage: Stage, fraction: float, message: str) -> None:
        """Report that `stage` is `fraction` (0 to 1) done."""
        ...


class Analyzer(Protocol):
    def analyze(self, audio_path: Path, options: AnalyzeOptions, progress: ProgressSink) -> Report:
        """Analyze one upload.

        Raises `AnalysisError` for anything the participant can fix. Any other exception is a
        bug and is reported as `ErrorCode.INTERNAL`. Calls must be safe to run concurrently.
        """
        ...
