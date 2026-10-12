"""The public signal stage returns a complete, validated recording."""

from statistics import median

from speech_delivery.analysis.constants import HOP_S
from speech_delivery.analysis.signal import analyze_signal
from speech_delivery.contract import FeatureName, RecordingFeatures, WordAlignment

from .synth import synth_speech


def test_analyze_signal() -> None:
    transcript = "We speak clearly."
    audio, truth = synth_speech(transcript)
    recording = analyze_signal(audio, transcript)
    assert tuple(word.text for word in recording.alignment.words) == ("We", "speak", "clearly.")
    assert abs(recording.alignment.words[-1].end - truth.words[-1].end) < 0.15
    assert recording.features.duration_s == audio.duration_s
    assert len(recording.features.tracks) == 6
    assert recording.features.mfcc is not None
    assert recording.features.track(FeatureName.PITCH).hop_s == HOP_S == 0.01
    assert (
        median(
            value
            for value in recording.features.track(FeatureName.PITCH).values
            if value is not None
        )
        < 0.01
    )
    assert (
        WordAlignment.model_validate_json(recording.alignment.model_dump_json())
        == recording.alignment
    )
    assert (
        RecordingFeatures.model_validate_json(recording.features.model_dump_json())
        == recording.features
    )
