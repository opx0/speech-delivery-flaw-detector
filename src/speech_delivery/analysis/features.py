"""Deterministic acoustics on the shared, sample-centred 10 ms grid.

Silence is energy below speech p95 minus 25 dB in aligned gaps, or minus 35 dB
inside words. Energy thus confirms/refines gaps and finds long within-word
hesitations without declaring quiet consonants to be pauses. Runs shorter than
PAUSE_MIN_S are discarded. Pitch octave outliers are folded toward a centred
310 ms median only when a >=9 semitone jump becomes <=3 semitones after folding.
"""

import warnings
from math import floor

import librosa
import numpy as np
import parselmouth
from numpy.typing import NDArray
from scipy.ndimage import median_filter

from ..audio import SAMPLE_RATE, Audio
from ..contract import (
    ErrorCode,
    FeatureName,
    FeatureTrack,
    Interval,
    MatrixTrack,
    RecordingFeatures,
    SpeakerNorm,
    WordAlignment,
)
from .constants import HOP_S, N_MFCC, PAUSE_MIN_S
from .protocol import AnalysisError

FloatArray = NDArray[np.float64]


def _energy(audio: Audio, n: int) -> FloatArray:
    size = round(0.025 * SAMPLE_RATE)
    hop = round(HOP_S * SAMPLE_RATE)
    padded = np.pad(audio.samples.astype(np.float64), (size // 2, size))
    frames = np.lib.stride_tricks.sliding_window_view(padded, size)[::hop][:n]
    window = np.hanning(size)
    power = np.sum(np.square(frames * window), axis=1) / np.sum(window**2)
    # The floor is applied after speaker normalisation, so gain shifts remain exact.
    return 10 * np.log10(np.maximum(power, 1e-16))


def _on_grid(values: FloatArray, x1: float, dx: float, times: FloatArray) -> FloatArray:
    """Nearest Praat frame, with no interpolation across unvoiced speech or edges."""
    indices = np.floor((times - x1) / dx + 0.5).astype(np.int64)
    valid = (indices >= 0) & (indices < len(values))
    result = np.full(len(times), np.nan)
    result[valid] = values[indices[valid]]
    return result


def _pitch(sound: parselmouth.Sound, times: FloatArray) -> tuple[FloatArray, float]:
    pitch = sound.to_pitch_ac(
        time_step=HOP_S,
        pitch_floor=60.0,
        pitch_ceiling=500.0,
        max_number_of_candidates=15,
        very_accurate=False,
        silence_threshold=0.03,
        voicing_threshold=0.45,
        octave_cost=0.01,
        octave_jump_cost=0.35,
        voiced_unvoiced_cost=0.14,
    )
    raw = np.asarray(pitch.selected_array["frequency"], dtype=np.float64)
    raw[raw <= 0] = np.nan
    hz = _on_grid(raw, pitch.x1, pitch.dx, times)
    voiced = np.isfinite(hz)
    if np.count_nonzero(voiced) < 30:
        warnings.warn(
            "Fewer than 30 voiced frames: speaker F0 is unreliable; "
            "using the observed median, or 150 Hz if no voice is detected.",
            RuntimeWarning,
            stacklevel=3,
        )
    if not np.any(voiced):
        return hz, 150.0
    absolute = 12 * np.log2(hz[voiced])
    filled = np.interp(times, times[voiced], absolute)
    local = median_filter(filled, size=31, mode="nearest")[voiced]
    difference = absolute - local
    folded = absolute - 12 * np.rint(difference / 12)
    repair = (np.abs(difference) >= 9) & (np.abs(folded - local) <= 3)
    absolute[repair] = folded[repair]
    hz[voiced] = np.exp2(absolute / 12)
    median = float(np.median(hz[voiced]))
    result = np.full(len(times), np.nan)
    result[voiced] = 12 * np.log2(hz[voiced] / median)
    return result, median


def _variation(pitch: FloatArray) -> FloatArray:
    voiced = np.isfinite(pitch)
    values = np.nan_to_num(pitch)
    indices = np.arange(len(pitch))
    radius = round(0.75 / HOP_S)
    left = np.maximum(0, indices - radius)
    right = np.minimum(len(pitch), indices + radius + 1)
    count = (
        np.concatenate(([0], np.cumsum(voiced)))[right]
        - np.concatenate(([0], np.cumsum(voiced)))[left]
    )
    total = np.concatenate(([0.0], np.cumsum(values)))
    squares = np.concatenate(([0.0], np.cumsum(values**2)))
    denominator = np.maximum(count, 1)
    mean = (total[right] - total[left]) / denominator
    variance = (squares[right] - squares[left]) / denominator - mean**2
    return np.where(count >= 30, np.sqrt(np.maximum(variance, 0)), np.nan)


def _pauses(
    energy: FloatArray, speech: NDArray[np.bool_], reference: float, duration: float
) -> tuple[Interval, ...]:
    silent = energy < reference - np.where(speech, 35.0, 25.0)
    edges = np.diff(np.concatenate(([False], silent, [False])).astype(np.int8))
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    intervals: list[Interval] = []
    for first, last in zip(starts, ends, strict=True):
        start = max(0.0, float(first) * HOP_S - HOP_S / 2)
        end = min(duration, float(last) * HOP_S - HOP_S / 2)
        if end - start >= PAUSE_MIN_S - 1e-9:
            intervals.append(Interval(start=start, end=end))
    return tuple(intervals)


def _rate(times: FloatArray, alignment: WordAlignment, duration: float) -> FloatArray:
    rate = np.zeros(len(times))
    for word in alignment.words:
        distance = times - (word.start + word.end) / 2
        inside = np.abs(distance) <= 1.0
        # Unit-mean Hann (twice the usual window) preserves words/s, rather than half-rate.
        rate[inside] += 1 + np.cos(np.pi * distance[inside])
    length = np.minimum(duration, times + 1.0) - np.maximum(0, times - 1.0)
    return rate / length


def extract_features(audio: Audio, alignment: WordAlignment) -> RecordingFeatures:
    """Extract all six features and MFCCs, with visible low-voicing fallbacks."""
    duration = audio.duration_s
    if duration <= 0 or not np.all(np.isfinite(audio.samples)):
        raise AnalysisError(ErrorCode.UNSUPPORTED_AUDIO, "Audio must contain finite samples.")
    if alignment.words[-1].end > duration + 1e-3:
        raise AnalysisError(ErrorCode.ALIGNMENT_FAILED, "Alignment extends beyond the audio.")
    n = floor(duration / HOP_S) + 1
    times = np.arange(n, dtype=np.float64) * HOP_S
    speech = np.zeros(n, dtype=np.bool_)
    for word in alignment.words:
        speech |= (times >= word.start) & (times < word.end)
    energy = _energy(audio, n)
    if np.any(speech):
        reference = float(np.percentile(energy[speech], 95))
    else:
        warnings.warn(
            "No grid frames inside aligned words; using all energy frames.",
            RuntimeWarning,
            stacklevel=2,
        )
        reference = float(np.percentile(energy, 95))
    if reference <= -100:
        warnings.warn(
            "No measurable speech energy; using a 0 dB reference and the -80 dB floor.",
            RuntimeWarning,
            stacklevel=2,
        )
        reference = 0.0
    # Praat requires at least three periods at 60 Hz. Padding is never exposed as voiced data.
    samples = np.pad(audio.samples, (0, max(0, round(0.1 * SAMPLE_RATE) - len(audio.samples))))
    sound = parselmouth.Sound(samples.astype(np.float64), sampling_frequency=SAMPLE_RATE)
    pitch, median = _pitch(sound, times)
    # Voicing estimates in quiet aligned gaps can be background periodicity, not speech.
    # Exclude those frames before pitch-variation windows spread them into adjacent words.
    pitch[(~speech) & (energy < reference - 25.0)] = np.nan
    harmonicity = sound.to_harmonicity_cc(
        time_step=HOP_S, minimum_pitch=60.0, silence_threshold=0.1, periods_per_window=1.0
    )
    clarity = _on_grid(
        np.asarray(harmonicity.values[0], dtype=np.float64), harmonicity.x1, harmonicity.dx, times
    )
    clarity[(~np.isfinite(pitch)) | (clarity <= -200)] = np.nan
    pauses = _pauses(energy, speech, reference, duration)
    left = np.maximum(0, times - 0.25)
    right = np.minimum(duration, times + 0.25)
    silent_time = np.zeros(n)
    for pause in pauses:
        silent_time += np.maximum(0, np.minimum(right, pause.end) - np.maximum(left, pause.start))
    tracks = (
        (FeatureName.SPEECH_RATE, _rate(times, alignment, duration)),
        (FeatureName.PITCH, pitch),
        (FeatureName.PITCH_VARIATION, _variation(pitch)),
        (FeatureName.ENERGY, np.maximum(-80.0, energy - reference)),
        (FeatureName.PAUSE, np.clip(silent_time / (right - left), 0, 1)),
        (FeatureName.CLARITY, clarity),
    )
    coefficients = librosa.feature.mfcc(
        y=np.pad(audio.samples, (0, max(0, 512 - len(audio.samples)))),
        sr=SAMPLE_RATE,
        n_mfcc=N_MFCC,
        n_fft=512,
        hop_length=round(HOP_S * SAMPLE_RATE),
        win_length=round(0.025 * SAMPLE_RATE),
        window="hann",
        center=True,
        pad_mode="constant",
        n_mels=40,
        fmin=60.0,
        fmax=SAMPLE_RATE / 2,
    )
    return RecordingFeatures(
        duration_s=duration,
        norm=SpeakerNorm(median_f0_hz=median, energy_reference_db=reference),
        tracks=tuple(
            FeatureTrack(
                name=name,
                hop_s=HOP_S,
                values=tuple(float(value) if np.isfinite(value) else None for value in values),
            )
            for name, values in tracks
        ),
        mfcc=MatrixTrack(
            hop_s=HOP_S,
            frames=tuple(tuple(float(value) for value in frame) for frame in coefficients.T[:n]),
        ),
        pauses=pauses,
    )
