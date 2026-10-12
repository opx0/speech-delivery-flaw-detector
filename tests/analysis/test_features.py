"""Literal acoustic expectations, not mocks of the signal implementation."""

from math import floor
from statistics import mean, median

import numpy as np
import pytest

from speech_delivery.analysis.constants import HOP_S, N_MFCC
from speech_delivery.analysis.features import extract_features
from speech_delivery.audio import SAMPLE_RATE, Audio, from_samples
from speech_delivery.contract import (
    FeatureName,
    RecordingFeatures,
    Word,
    WordAlignment,
    WordSpan,
)

from .synth import synth_speech, synth_variant

_TEXT = "The bright morning brings new hope. We speak clearly and listen carefully."


def _defined(features: RecordingFeatures, name: FeatureName) -> tuple[float, ...]:
    return tuple(value for value in features.track(name).values if value is not None)


@pytest.fixture(scope="module")
def speech() -> tuple[Audio, WordAlignment, RecordingFeatures]:
    audio, alignment = synth_speech(_TEXT, pauses={5: 1.0})
    return audio, alignment, extract_features(audio, alignment)


def test_grid_contract_and_reproducibility(
    speech: tuple[Audio, WordAlignment, RecordingFeatures],
) -> None:
    audio, alignment, features = speech
    n = floor(audio.duration_s / HOP_S) + 1
    assert tuple(track.name for track in features.tracks) == tuple(FeatureName)
    assert all(track.hop_s == 0.01 and len(track.values) == n for track in features.tracks)
    assert features.mfcc is not None
    assert features.mfcc.hop_s == 0.01
    assert len(features.mfcc.frames) == n
    assert all(len(frame) == N_MFCC == 13 for frame in features.mfcc.frames)
    assert RecordingFeatures.model_validate_json(features.model_dump_json()) == features
    assert extract_features(audio, alignment).model_dump_json() == features.model_dump_json()
    assert median(_defined(features, FeatureName.PITCH)) == pytest.approx(0, abs=0.001)
    assert median(_defined(features, FeatureName.CLARITY)) > 5


def test_rate_follows_render_speed() -> None:
    slow_audio, slow_words = synth_speech(_TEXT, speed=120, gap_s=0)
    fast_audio, fast_words = synth_speech(_TEXT, speed=240, gap_s=0)
    slow = mean(_defined(extract_features(slow_audio, slow_words), FeatureName.SPEECH_RATE))
    fast = mean(_defined(extract_features(fast_audio, fast_words), FeatureName.SPEECH_RATE))
    assert slow == pytest.approx(1.84, abs=0.15)
    assert fast == pytest.approx(3.89, abs=0.2)
    assert fast / slow == pytest.approx(2, rel=0.12)
    assert fast / slow == pytest.approx(slow_audio.duration_s / fast_audio.duration_s, rel=0.05)


def test_inserted_silence_and_energy_refinement(
    speech: tuple[Audio, WordAlignment, RecordingFeatures],
) -> None:
    audio, alignment, features = speech
    (pause,) = features.pauses
    assert pause.start == pytest.approx(alignment.words[5].end, abs=0.025)
    assert pause.end - pause.start == pytest.approx(1.0, abs=0.025)
    centre = round((pause.start + pause.end) / 2 / HOP_S)
    assert features.track(FeatureName.PAUSE).values[centre] == 1.0
    # Hide the gap inside a single word. Energy must still discover the hesitation.
    hidden = WordAlignment(
        words=(Word(text="passage", start=0, end=audio.duration_s, confidence=1),),
        sentences=(WordSpan(first=0, last=0),),
    )
    detected = extract_features(audio, hidden).pauses
    assert len(detected) == 1
    assert detected[0].start == pytest.approx(pause.start, abs=0.025)
    assert detected[0].end - detected[0].start == pytest.approx(1.0, abs=0.025)


def test_gain_is_removed_only_by_own_reference(
    speech: tuple[Audio, WordAlignment, RecordingFeatures],
) -> None:
    audio, alignment, original = speech
    quiet = extract_features(from_samples(audio.samples * 10 ** (-12 / 20)), alignment)
    assert quiet.norm.energy_reference_db - original.norm.energy_reference_db == pytest.approx(
        -12, abs=0.001
    )
    left = original.track(FeatureName.ENERGY).values
    right = quiet.track(FeatureName.ENERGY).values
    assert (
        max(abs(a - b) for a, b in zip(left, right, strict=True) if a is not None and b is not None)
        < 0.001
    )
    fixed_reference = tuple(
        value + quiet.norm.energy_reference_db - original.norm.energy_reference_db
        for value in right
        if value is not None and value > -70
    )
    original_speech = tuple(value for value in left if value is not None and value > -70)
    assert mean(fixed_reference) - mean(original_speech) == pytest.approx(-12, abs=0.001)


def test_pitch_is_speaker_relative() -> None:
    low_audio, low_words = synth_speech(_TEXT, pitch=30)
    high_audio, high_words = synth_variant(_TEXT)
    low = extract_features(low_audio, low_words)
    high = extract_features(high_audio, high_words)
    assert high.norm.median_f0_hz / low.norm.median_f0_hz > 2
    assert median(_defined(low, FeatureName.PITCH)) == pytest.approx(0, abs=0.001)
    assert median(_defined(high, FeatureName.PITCH)) == pytest.approx(0, abs=0.001)


def test_flat_tone_has_less_variation() -> None:
    time = np.arange(4 * SAMPLE_RATE) / SAMPLE_RATE
    alignment = WordAlignment(
        words=(Word(text="tone", start=0, end=4, confidence=1),),
        sentences=(WordSpan(first=0, last=0),),
    )
    flat = from_samples(0.2 * np.sin(2 * np.pi * 150 * time))
    frequency = 150 * np.exp2(4 * np.sin(2 * np.pi * 2 * time) / 12)
    lively = from_samples(0.2 * np.sin(2 * np.pi * np.cumsum(frequency) / SAMPLE_RATE))
    flat_variation = median(
        _defined(extract_features(flat, alignment), FeatureName.PITCH_VARIATION)
    )
    lively_variation = median(
        _defined(extract_features(lively, alignment), FeatureName.PITCH_VARIATION)
    )
    assert flat_variation < 0.01
    assert lively_variation == pytest.approx(2.82, abs=0.15)


@pytest.mark.parametrize("duration", [0.01, 1.0])
def test_no_voice_has_visible_fallback(duration: float) -> None:
    audio = from_samples(np.zeros(round(duration * SAMPLE_RATE), dtype=np.float32))
    alignment = WordAlignment(
        words=(Word(text="silence", start=0, end=duration, confidence=1),),
        sentences=(WordSpan(first=0, last=0),),
    )
    with pytest.warns(RuntimeWarning, match="No measurable speech energy|Fewer than 30 voiced"):
        features = extract_features(audio, alignment)
    assert features.norm.median_f0_hz == 150
    assert features.norm.energy_reference_db == 0
    assert set(features.track(FeatureName.PITCH).values) == {None}
    assert set(features.track(FeatureName.PITCH_VARIATION).values) == {None}
    assert set(features.track(FeatureName.CLARITY).values) == {None}
    assert set(features.track(FeatureName.ENERGY).values) == {-80.0}
