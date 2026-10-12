"""Measured MMS behaviour on speech with independent sample-clock ground truth."""

from concurrent.futures import ThreadPoolExecutor
from statistics import median

import numpy as np
import pytest

from speech_delivery.analysis.align import align
from speech_delivery.analysis.protocol import AnalysisError
from speech_delivery.audio import Audio, from_samples
from speech_delivery.contract import ErrorCode, WordAlignment, WordSpan

from .synth import synth_speech

_TEXT = "The bright morning brings new hope. We speak clearly and listen carefully."
_WRONG = (
    "Purple elephants wander beneath frozen oceans. Ancient machines destroy every distant planet."
)


@pytest.fixture(scope="session")
def aligned() -> tuple[Audio, WordAlignment, tuple[WordAlignment, ...]]:
    audio, truth = synth_speech(_TEXT, pauses={5: 1.0})
    return audio, truth, tuple(align(audio, _TEXT) for _ in range(3))


def test_boundaries_quotes_confidence_and_determinism(
    aligned: tuple[Audio, WordAlignment, tuple[WordAlignment, ...]],
) -> None:
    audio, truth, results = aligned
    actual = results[0]
    errors = [
        abs(getattr(observed, edge) - getattr(expected, edge))
        for observed, expected in zip(actual.words, truth.words, strict=True)
        for edge in ("start", "end")
    ]
    # Measured 39.8 ms median, 160 ms maximum. 100 ms allows phone/CTC endpoint differences.
    assert median(errors) < 0.10
    assert max(errors) < 0.25
    assert tuple(word.text for word in actual.words) == tuple(word.text for word in truth.words)
    assert actual.sentences == (WordSpan(first=0, last=5), WordSpan(first=6, last=11))
    assert all(a.end <= b.start for a, b in zip(actual.words, actual.words[1:], strict=False))
    assert all(0 <= word.confidence <= 1 for word in actual.words)
    assert actual.words[-1].end <= audio.duration_s
    assert median(word.confidence for word in actual.words) > 0.85
    assert len({result.model_dump_json() for result in results}) == 1
    assert WordAlignment.model_validate_json(actual.model_dump_json()) == actual


def test_wrong_transcript(aligned: tuple[Audio, WordAlignment, tuple[WordAlignment, ...]]) -> None:
    with pytest.raises(AnalysisError, match="character confidence") as caught:
        align(aligned[0], _WRONG)
    assert caught.value.code is ErrorCode.TRANSCRIPT_MISMATCH


@pytest.mark.parametrize("transcript", ["We have 12 apples.", "--- !!!", "\uff11\uff12 apples"])
def test_unsupported_transcript(transcript: str) -> None:
    with pytest.raises(AnalysisError) as caught:
        align(from_samples(np.zeros(1600, dtype=np.float32)), transcript)
    assert caught.value.code is ErrorCode.TRANSCRIPT_MISMATCH


def test_too_many_characters() -> None:
    with pytest.raises(AnalysisError, match="too short") as caught:
        align(from_samples(np.zeros(1600, dtype=np.float32)), "extraordinarily long transcript")
    assert caught.value.code is ErrorCode.ALIGNMENT_FAILED


def test_concurrent_calls(aligned: tuple[Audio, WordAlignment, tuple[WordAlignment, ...]]) -> None:
    audio, _, expected = aligned
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(align, audio, _TEXT) for _ in range(2)]
        assert [future.result() for future in futures] == [expected[0], expected[0]]


def test_stitching_crosses_thirty_seconds() -> None:
    text = " ".join([_TEXT] * 6)
    audio, truth = synth_speech(text)
    assert 30 < audio.duration_s < 40
    actual = align(audio, text)
    assert len(actual.words) == 72
    assert (
        median(abs(a.start - b.start) for a, b in zip(actual.words, truth.words, strict=True))
        < 0.10
    )
    assert abs(actual.words[-1].end - truth.words[-1].end) < 0.15
    assert all(a.end <= b.start for a, b in zip(actual.words, actual.words[1:], strict=False))
