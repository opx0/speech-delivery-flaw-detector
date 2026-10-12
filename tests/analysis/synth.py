"""Deterministic, independently rendered words with exact sample-clock boundaries."""

import io
import subprocess
from collections.abc import Mapping
from functools import lru_cache
from math import gcd
from typing import cast

import numpy as np
import soundfile as sf
from numpy.typing import NDArray
from scipy.signal import resample_poly  # pyright: ignore[reportUnknownVariableType]

from speech_delivery.audio import SAMPLE_RATE, Audio, from_samples
from speech_delivery.contract import Word, WordAlignment
from speech_delivery.text import sentence_spans, tokens


@lru_cache(maxsize=512)
def _render(word: str, voice: str, pitch: int, speed: int) -> NDArray[np.float32]:
    result = subprocess.run(
        ["espeak-ng", "--stdout", "-v", voice, "-p", str(pitch), "-s", str(speed), "--", word],
        capture_output=True,
        check=True,
        timeout=10,
    )
    samples, rate = sf.read(io.BytesIO(result.stdout), dtype="float32")
    divisor = gcd(rate, SAMPLE_RATE)
    waveform = cast(
        NDArray[np.float32],
        np.asarray(
            resample_poly(samples, SAMPLE_RATE // divisor, rate // divisor), dtype=np.float32
        ),
    )
    # Remove espeak's utterance padding, not quiet phones. These sample boundaries are truth.
    active = np.flatnonzero(np.abs(waveform) > 0.0001)
    if not len(active):
        raise ValueError(f"espeak produced no speech for {word!r}")
    return waveform[int(active[0]) : int(active[-1]) + 1]


def synth_speech(
    transcript: str,
    *,
    speed: int = 175,
    voice: str = "en-us",
    pitch: int = 50,
    gap_s: float = 0.08,
    pauses: Mapping[int, float] | None = None,
) -> tuple[Audio, WordAlignment]:
    """Render words separately. `pauses[i]` replaces the gap after zero-based word i."""
    written = tokens(transcript)
    chunks: list[NDArray[np.float32]] = []
    words: list[Word] = []
    cursor = 0
    for index, text in enumerate(written):
        samples = _render(text, voice, pitch, speed)
        words.append(
            Word(
                text=text,
                start=cursor / SAMPLE_RATE,
                end=(cursor + len(samples)) / SAMPLE_RATE,
                confidence=1.0,
            )
        )
        chunks.append(samples)
        cursor += len(samples)
        if index < len(written) - 1:
            gap = gap_s if pauses is None else pauses.get(index, gap_s)
            if gap < 0:
                raise ValueError("silence lengths must be nonnegative")
            silence = np.zeros(round(gap * SAMPLE_RATE), dtype=np.float32)
            chunks.append(silence)
            cursor += len(silence)
    if not chunks:
        raise ValueError("synthetic speech needs at least one word")
    return from_samples(np.concatenate(chunks)), WordAlignment(
        words=tuple(words), sentences=sentence_spans(written)
    )


def synth_variant(
    transcript: str, *, voice: str = "en-us+f3", pitch: int = 70, speed: int = 175
) -> tuple[Audio, WordAlignment]:
    """The same construction with a different speaker's voice and base pitch."""
    return synth_speech(transcript, voice=voice, pitch=pitch, speed=speed)
