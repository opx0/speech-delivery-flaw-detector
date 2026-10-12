"""A recording after the signal stage: its words and its acoustic features, no audio."""

from dataclasses import dataclass

from ..contract import RecordingFeatures, WordAlignment


@dataclass(frozen=True, slots=True)
class Recording:
    """Everything the comparison needs about one reading. Built by `signal.analyze_signal`."""

    alignment: WordAlignment
    features: RecordingFeatures
