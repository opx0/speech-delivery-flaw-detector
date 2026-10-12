import hashlib
from itertools import pairwise

import numpy as np
import pytest
from numpy.typing import NDArray

from speech_delivery.audio import SAMPLE_RATE, Audio
from speech_delivery.contract.alignment import WordAlignment, WordSpan
from speech_delivery.contract.dataset import (
    DragParams,
    FlawLabel,
    HesitationParams,
    MonotoneParams,
    PauseCollapseParams,
    RushParams,
)
from speech_delivery.contract.taxonomy import FlawKind
from speech_delivery.dataset.inject import Injected, make_control, make_flawed, make_speaker_shifted
from speech_delivery.dataset.levels import parameters
from speech_delivery.dataset.regions import select_regions

from .synth_speech import f0, rms, synth_speech


@pytest.fixture(scope="module")
def speech() -> tuple[Audio, WordAlignment]:
    return synth_speech()


@pytest.fixture(scope="module")
def control(speech: tuple[Audio, WordAlignment]) -> Injected:
    return make_control(*speech)


def segment(audio: Audio, start: float, end: float) -> NDArray[np.float32]:
    return audio.samples[round(start * SAMPLE_RATE) : round(end * SAMPLE_RATE)]


def pitch_spread(audio: Audio, start: float, end: float) -> float:
    return float(np.std(12 * np.log2(f0(segment(audio, start, end)))))


def assert_valid(result: Injected) -> None:
    WordAlignment.model_validate(result.alignment.model_dump())
    assert result.audio.samples.dtype == np.float32
    assert np.isfinite(result.audio.samples).all()
    assert np.max(np.abs(result.audio.samples)) <= 1
    for flaw in result.flaws:
        assert FlawLabel.model_validate(flaw.model_dump()) == flaw
        assert 0 <= flaw.start < flaw.end <= result.audio.duration_s
        assert result.alignment.time_range(flaw.words) == (flaw.start, flaw.end)
    assert all(a.end <= b.start for a, b in pairwise(result.flaws))


@pytest.mark.parametrize("kind", list(FlawKind))
def test_level_three_acoustics(
    speech: tuple[Audio, WordAlignment], control: Injected, kind: FlawKind
) -> None:
    audio, original = speech
    result = make_flawed(audio, original, (kind,), 3, 19)
    assert 2 <= len(result.flaws) <= 4
    assert_valid(result)
    delta = 0.0
    covered: set[int] = set()
    for flaw in result.flaws:
        params = flaw.injection
        assert params is not None
        covered.update(range(flaw.words.first, flaw.words.last + 1))
        old_start, old_end = original.time_range(flaw.words)
        if isinstance(params, (RushParams, DragParams)):
            expected = (old_end - old_start) / params.rate_factor
            assert flaw.end - flaw.start == pytest.approx(expected, abs=2 / SAMPLE_RATE)
            delta += expected - (old_end - old_start)
            for index in range(flaw.words.first, flaw.words.last + 1):
                old, new = original.words[index], result.alignment.words[index]
                assert new.end - new.start == pytest.approx(
                    (old.end - old.start) / params.rate_factor, abs=2 / SAMPLE_RATE
                )
        elif isinstance(params, MonotoneParams):
            retained = pitch_spread(result.audio, flaw.start, flaw.end) / pitch_spread(
                control.audio, old_start, old_end
            )
            assert retained == pytest.approx(params.pitch_excursion_retained, abs=0.12)
        elif isinstance(params, HesitationParams):
            site = params.silences[0]
            before = result.alignment.words[site.after_word]
            after = result.alignment.words[site.after_word + 1]
            old_gap = (
                original.words[site.after_word + 1].start - original.words[site.after_word].end
            )
            assert after.start - before.end == pytest.approx(old_gap + 0.9, abs=2 / SAMPLE_RATE)
            gap = segment(result.audio, before.end, after.start)
            assert np.count_nonzero(gap == 0) >= round(0.9 * SAMPLE_RATE)
            assert not before.text.rstrip("\"')]}\u201d\u2019").endswith(tuple(",.;:!?"))
            delta += 0.9
        elif isinstance(params, PauseCollapseParams):
            index = flaw.words.first
            old_gap = original.words[index + 1].start - original.words[index].end
            new_gap = result.alignment.words[index + 1].start - result.alignment.words[index].end
            assert old_gap >= 0.3
            assert new_gap == pytest.approx(old_gap * 0.2, abs=2 / SAMPLE_RATE)
            delta -= old_gap * 0.8
        else:
            old_tail = segment(control.audio, old_end - 0.04, old_end)
            new_tail = segment(result.audio, flaw.end - 0.04, flaw.end)
            drop = 20 * np.log10(rms(old_tail) / rms(new_tail))
            assert drop == pytest.approx(10, abs=0.6)
    assert result.audio.duration_s == pytest.approx(audio.duration_s + delta, abs=5 / SAMPLE_RATE)
    for index, (old, new) in enumerate(zip(original.words, result.alignment.words, strict=True)):
        if index not in covered:
            assert new.end - new.start == pytest.approx(old.end - old.start, abs=2 / SAMPLE_RATE)
            expected = segment(control.audio, old.start, old.end)
            actual = segment(result.audio, new.start, new.end)
            assert np.array_equal(actual, expected)


@pytest.mark.parametrize("kind", list(FlawKind))
def test_measured_severity_strictly_increases(
    speech: tuple[Audio, WordAlignment], control: Injected, kind: FlawKind
) -> None:
    audio, alignment = speech
    quantities: list[float] = []
    spans: list[tuple[WordSpan, ...]] = []
    for level in range(1, 5):
        result = make_flawed(audio, alignment, (kind,), level, 19)
        spans.append(tuple(flaw.words for flaw in result.flaws))
        measurements: list[float] = []
        for flaw in result.flaws:
            start, end = alignment.time_range(flaw.words)
            if kind is FlawKind.RUSH:
                measurements.append((end - start) / (flaw.end - flaw.start))
            elif kind is FlawKind.DRAG:
                measurements.append((flaw.end - flaw.start) / (end - start))
            elif kind is FlawKind.MONOTONE:
                measurements.append(-pitch_spread(result.audio, flaw.start, flaw.end))
            elif kind is FlawKind.HESITATION:
                assert isinstance(flaw.injection, HesitationParams)
                i = flaw.injection.silences[0].after_word
                measurements.append(
                    result.alignment.words[i + 1].start - result.alignment.words[i].end
                )
            elif kind is FlawKind.PAUSE_COLLAPSE:
                i = flaw.words.first
                measurements.append(
                    -(result.alignment.words[i + 1].start - result.alignment.words[i].end)
                )
            else:
                measurements.append(
                    20
                    * np.log10(
                        rms(segment(control.audio, end - 0.04, end))
                        / rms(segment(result.audio, flaw.end - 0.04, flaw.end))
                    )
                )
        quantities.append(float(np.mean(measurements)))
    assert all(span == spans[0] for span in spans)
    assert all(a < b for a, b in pairwise(quantities)), quantities


def test_control_and_speaker_shift(speech: tuple[Audio, WordAlignment], control: Injected) -> None:
    audio, alignment = speech
    assert control.flaws == ()
    assert control.alignment == alignment
    error = audio.samples - control.audio.samples
    snr = 10 * np.log10(np.sum(audio.samples**2) / np.sum(error**2))
    assert snr > 35
    assert np.corrcoef(audio.samples, control.audio.samples)[0, 1] > 0.999
    shifted = make_speaker_shifted(audio, alignment, 3.0, 1.1)
    assert shifted.flaws == ()
    assert shifted.alignment == alignment
    assert shifted.audio.duration_s == audio.duration_s
    measured = 12 * np.log2(np.median(f0(shifted.audio.samples)) / np.median(f0(audio.samples)))
    assert measured == pytest.approx(3.0, abs=0.5)
    assert_valid(shifted)
    assert np.array_equal(
        make_speaker_shifted(audio, alignment, 0, 1).audio.samples, control.audio.samples
    )


@pytest.mark.parametrize("kind", list(FlawKind))
def test_determinism(speech: tuple[Audio, WordAlignment], kind: FlawKind) -> None:
    first = make_flawed(*speech, (kind,), 3, 19)
    second = make_flawed(*speech, (kind,), 3, 19)
    assert first.flaws == second.flaws
    assert (
        hashlib.sha256(first.audio.samples.tobytes()).digest()
        == hashlib.sha256(second.audio.samples.tobytes()).digest()
    )
    assert select_regions(speech[1], (kind,), 19) != select_regions(speech[1], (kind,), 20)


def test_compound_and_short_clip(speech: tuple[Audio, WordAlignment]) -> None:
    result = make_flawed(*speech, (FlawKind.RUSH, FlawKind.HESITATION), 3, 19)
    assert {f.kind for f in result.flaws} == {FlawKind.RUSH, FlawKind.HESITATION}
    assert all(
        sum(f.kind == kind for f in result.flaws) >= 2
        for kind in (FlawKind.RUSH, FlawKind.HESITATION)
    )
    assert_valid(result)
    short = synth_speech("We find hope.")
    rushed = make_flawed(*short, (FlawKind.RUSH,), 3, 19)
    assert len(rushed.flaws) == 1
    assert rushed.flaws[0].words.first == 0
    assert rushed.flaws[0].words.last == 2
    assert make_flawed(*short, (FlawKind.PAUSE_COLLAPSE,), 3, 19).flaws == ()
    assert parameters(FlawKind.RUSH, 3) == RushParams(rate_factor=1.5)


@pytest.mark.parametrize("level", [0, 5])
def test_invalid_level(speech: tuple[Audio, WordAlignment], level: int) -> None:
    with pytest.raises(ValueError, match="level"):
        make_flawed(*speech, (FlawKind.RUSH,), level, 19)


def test_duplicate_kinds(speech: tuple[Audio, WordAlignment]) -> None:
    with pytest.raises(ValueError, match="duplicates"):
        make_flawed(*speech, (FlawKind.RUSH, FlawKind.RUSH), 3, 19)
