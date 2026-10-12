"""Deterministic local PSOLA and sample-domain edits, with an explicit clock map.

Praat's neutral overlap-add does not preserve waveform phase. A shared 1% wet
neutral pass keeps controls close to gold without making processing exclusive to
flawed clips. Local pitch/rate transformations necessarily use full-wet PSOLA.
"""

from dataclasses import dataclass
from itertools import pairwise

import numpy as np
import parselmouth
from numpy.typing import NDArray
from parselmouth.praat import call, run
from scipy.signal import resample

from speech_delivery.audio import SAMPLE_RATE, Audio, from_samples

Samples = NDArray[np.float32]


def sample_index(time: float) -> int:
    return round(time * SAMPLE_RATE)


def peak_safe(samples: Samples) -> Audio:
    peak = float(np.max(np.abs(samples))) if len(samples) else 0.0
    return from_samples(samples / max(1.0, peak))


def _fit(samples: NDArray[np.float64], length: int) -> Samples:
    # Praat may round its duration by a sample; fit to the clock used for labels.
    if len(samples) != length:
        samples = np.asarray(resample(samples, length), dtype=np.float64)
    return np.asarray(samples, dtype=np.float32)


def psola(samples: Samples, rate: float = 1.0, retained: float = 1.0) -> Samples:
    # Praat draws random overlap-add positions for unvoiced stretches. Seeding right before each
    # resynthesis makes the same input give the same bytes.
    run("random_initializeWithSeedUnsafelyButPredictably (1)")
    sound = parselmouth.Sound(samples, SAMPLE_RATE)
    manipulation = call(sound, "To Manipulation", 0.01, 60, 450)
    if rate != 1:
        # Praat 6.1 randomly places unvoiced overlap-add windows when duration
        # changes. Fill only pulse gaps with a fixed surrogate schedule instead;
        # original voiced pulses stay intact and no global RNG is touched.
        pulses = call(manipulation, "Extract pulses")
        count = int(call(pulses, "Get number of points"))
        times = (
            [0.0]
            + [float(call(pulses, "Get time from index", i)) for i in range(1, count + 1)]
            + [sound.duration]
        )
        for left, right in pairwise(times):
            if right - left > 0.02:
                for time in np.arange(left + 0.005, right - 0.002, 0.005):
                    call(pulses, "Add point", float(time))
        call([pulses, manipulation], "Replace pulses")
        tier = call(manipulation, "Extract duration tier")
        call(tier, "Add point", 0.0, 1 / rate)
        call(tier, "Add point", sound.duration, 1 / rate)
        call([tier, manipulation], "Replace duration tier")
    if retained != 1:
        tier = call(manipulation, "Extract pitch tier")
        count = int(call(tier, "Get number of points"))
        times = [float(call(tier, "Get time from index", i)) for i in range(1, count + 1)]
        hz = np.asarray([float(call(tier, "Get value at index", i)) for i in range(1, count + 1)])
        if count:
            semitones = 12 * np.log2(hz)
            center = float(np.median(semitones))
            flattened = 2 ** ((center + retained * (semitones - center)) / 12)
            call(tier, "Remove points between", 0.0, sound.duration)
            for time, value in zip(times, flattened, strict=True):
                call(tier, "Add point", time, float(value))
            call([tier, manipulation], "Replace pitch tier")
    result = call(manipulation, "Get resynthesis (overlap-add)")
    return _fit(np.asarray(result.values[0], dtype=np.float64), round(len(samples) / rate))


def neutral(samples: Samples) -> Samples:
    if len(samples) < 640 or not np.any(samples):
        return samples.copy()
    wet = psola(samples)
    return np.asarray(0.99 * samples + 0.01 * wet, dtype=np.float32)


def crossfade_edges(original: Samples, changed: Samples) -> Samples:
    """Five-ms equal-power joins inside the segment, without stealing clock time."""
    result = changed.copy()
    if np.array_equal(original, changed):
        return result
    size = min(80, len(original) // 2, len(changed) // 2)
    if size:
        phase = np.linspace(0, np.pi / 2, size)
        result[:size] = original[:size] * np.cos(phase) + changed[:size] * np.sin(phase)
        result[-size:] = changed[-size:] * np.cos(phase) + original[-size:] * np.sin(phase)
    return result


def silence_edit(samples: Samples, length: int, insert: bool) -> Samples:
    if insert:
        middle = len(samples) // 2
        result = np.concatenate((samples[:middle], np.zeros(length, np.float32), samples[middle:]))
        boundaries = (middle, middle + length)
    else:
        keep = min(length, len(samples))
        left = keep // 2
        result = np.concatenate((samples[:left], samples[len(samples) - (keep - left) :]))
        boundaries = (left,)
    # Taper only the gap, never neighboring words; boundaries in voiced gold are de-clicked.
    for boundary in boundaries:
        size = min(80, boundary, len(result) - boundary)
        if size:
            phase = np.linspace(0, np.pi / 2, size)
            result[boundary - size : boundary] *= np.cos(phase)
            result[boundary : boundary + size] *= np.sin(phase)
    return np.asarray(result, dtype=np.float32)


def fade(samples: Samples, drop_db: float, fraction: float) -> Samples:
    size = max(1, round(len(samples) * fraction))
    envelope = np.ones(len(samples), dtype=np.float64)
    envelope[-size:] = 10 ** (-np.linspace(0, drop_db, size) / 20)
    return np.asarray(samples * envelope, dtype=np.float32)


def speaker_shift(samples: Samples, semitones: float, formant_ratio: float) -> Samples:
    sound = parselmouth.Sound(samples, SAMPLE_RATE)
    pitch = sound.to_pitch_ac(time_step=0.01, pitch_floor=60, pitch_ceiling=450)
    voiced = pitch.selected_array["frequency"]
    voiced = voiced[voiced > 0]
    if not len(voiced):
        raise ValueError("speaker shifting requires voiced audio")
    target = float(np.median(voiced)) * 2 ** (semitones / 12)
    shifted = call([sound, pitch], "Change gender", formant_ratio, target, 1.0, 1.0)
    return _fit(np.asarray(shifted.values[0], dtype=np.float64), len(samples))


@dataclass(frozen=True, slots=True)
class Edit:
    first: int
    last: int
    samples: Samples


@dataclass(frozen=True, slots=True)
class TimeMap:
    """Nondecreasing piecewise-linear seconds map; collapse may have a flat segment."""

    old: tuple[float, ...]
    new: tuple[float, ...]

    def __call__(self, time: float) -> float:
        return float(np.interp(time, self.old, self.new))


def splice(samples: Samples, edits: tuple[Edit, ...]) -> tuple[Samples, TimeMap]:
    chunks: list[Samples] = []
    old = [0.0]
    new = [0.0]
    cursor = 0
    out = 0
    for edit in edits:
        if edit.first < cursor or edit.last <= edit.first:
            raise ValueError("edits must have positive, disjoint, ordered extents")
        chunks.append(samples[cursor : edit.first])
        out += edit.first - cursor
        if edit.first > cursor:
            old.append(edit.first / SAMPLE_RATE)
            new.append(out / SAMPLE_RATE)
        chunks.append(edit.samples)
        out += len(edit.samples)
        old.append(edit.last / SAMPLE_RATE)
        new.append(out / SAMPLE_RATE)
        cursor = edit.last
    chunks.append(samples[cursor:])
    out += len(samples) - cursor
    if cursor < len(samples):
        old.append(len(samples) / SAMPLE_RATE)
        new.append(out / SAMPLE_RATE)
    return np.concatenate(chunks), TimeMap(tuple(old), tuple(new))
