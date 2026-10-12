"""Measures of how a participant's reading departs from a baseline reading of the same text.

Words are the unit. The participant's words are paired with the baseline's by text, which gives a
word-for-word map between the two clocks. Each measure is one number per participant word, signed
so that positive means the flaw direction. `calibration.Measure` names them.

The same module computes the windowed statistics that normative mode compares with bands.
"""

import math
import re
from dataclasses import dataclass
from difflib import SequenceMatcher

import numpy as np
from numpy.typing import NDArray

from ..contract import (
    ErrorCode,
    FeatureName,
    RecordingFeatures,
    WordAlignment,
)
from ..contract.report import WarpAnchor
from ..text import normalize
from .calibration import Measure, Stat
from .constants import HOP_S
from .protocol import AnalysisError
from .recording import Recording

FloatArray = NDArray[np.float64]

MIN_PAIRS = 5
MIN_PAIRED_SHARE = 0.5
MIN_WORD_S = 0.03
TAIL_WORDS = 4
SENTENCE_PAUSE_MIN_S = 0.4
WINDOW_S = 2.0
WINDOW_HOP_S = 1.0

_ANY_PUNCT = re.compile(r"[.,;:!?][\"')\u201d\u2019]*$")
_SENTENCE_END = re.compile(r"[.!?][\"')\u201d\u2019]*$")


def track(features: RecordingFeatures, name: FeatureName) -> FloatArray:
    values = features.track(name).values
    return np.array([math.nan if v is None else v for v in values], dtype=np.float64)


def mean_over(values: FloatArray, start: float, end: float) -> float:
    """Mean of the defined samples between two times, or nan when there are none."""
    low = max(0, round(start / HOP_S))
    high = min(len(values), round(end / HOP_S) + 1)
    segment = values[low:high]
    segment = segment[~np.isnan(segment)]
    return float(segment.mean()) if segment.size else math.nan


@dataclass(frozen=True, slots=True)
class Pairing:
    """`index[i]` is the baseline word that participant word `i` was matched to."""

    index: dict[int, int]
    warp: tuple[WarpAnchor, ...]

    def warp_times(self, times: FloatArray) -> FloatArray:
        """Participant clock to baseline clock. Beyond the ends the clocks run in step."""
        xp = np.array([a.participant_s for a in self.warp])
        fp = np.array([a.baseline_s for a in self.warp])
        mapped = np.interp(times, xp, fp)
        mapped = np.where(times < xp[0], fp[0] - (xp[0] - times), mapped)
        return np.where(times > xp[-1], fp[-1] + (times - xp[-1]), mapped)


def pair_words(participant: WordAlignment, baseline: WordAlignment) -> Pairing:
    left = [normalize(w.text) for w in participant.words]
    right = [normalize(w.text) for w in baseline.words]
    matcher = SequenceMatcher(a=left, b=right, autojunk=False)
    index: dict[int, int] = {}
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            index[block.a + offset] = block.b + offset
    if len(index) < MIN_PAIRS or len(index) < MIN_PAIRED_SHARE * len(left):
        raise AnalysisError(
            ErrorCode.TRANSCRIPT_MISMATCH,
            "The recording shares too few words with the library text to compare word by word.",
        )
    anchors: list[WarpAnchor] = []
    for i, j in sorted(index.items()):
        p, b = participant.words[i], baseline.words[j]
        anchors.append(WarpAnchor(participant_s=p.start, baseline_s=b.start))
        anchors.append(WarpAnchor(participant_s=p.end, baseline_s=b.end))
    return Pairing(index=index, warp=tuple(anchors))


def word_means(rec: Recording, name: FeatureName) -> FloatArray:
    values = track(rec.features, name)
    return np.array([mean_over(values, w.start, w.end) for w in rec.alignment.words])


def _sentence_levels(
    rec: Recording,
) -> tuple[FloatArray, NDArray[np.bool_], list[tuple[float, float]]]:
    """Per word level relative to its sentence, a mask of sentence-tail words, and for each
    sentence the pair (time of its last word, dB the tail sits below the rest of the sentence)."""
    means = word_means(rec, FeatureName.ENERGY)
    relative = np.full(len(means), math.nan)
    tail = np.zeros(len(means), dtype=bool)
    drops: list[tuple[float, float]] = []
    for span in rec.alignment.sentences:
        words = slice(span.first, span.last + 1)
        relative[words] = means[words] - np.nanmean(means[words])
        tail_first = max(span.first, span.last - TAIL_WORDS + 1)
        tail[tail_first : span.last + 1] = True
        head = means[span.first : tail_first]
        end = means[tail_first : span.last + 1]
        if head[~np.isnan(head)].size and end[~np.isnan(end)].size:
            last = rec.alignment.words[span.last]
            drops.append((last.end, float(np.nanmean(head) - np.nanmean(end))))
    return relative, tail, drops


def gap_after(alignment: WordAlignment, word: int) -> float:
    words = alignment.words
    return max(words[word + 1].start - words[word].end, 0.0)


def _centre(values: FloatArray) -> FloatArray:
    """Remove the reading's overall offset, so a slower or flatter speaker is not flagged
    everywhere. Only local departures from the speaker's own offset remain."""
    defined = values[~np.isnan(values)]
    return values - float(np.median(defined)) if defined.size else values


def _smooth(values: FloatArray) -> FloatArray:
    """Three-word moving mean that ignores undefined words. Undefined everywhere becomes zero."""
    out = np.zeros(len(values))
    for k in range(len(values)):
        segment = values[max(0, k - 1) : k + 2]
        segment = segment[~np.isnan(segment)]
        out[k] = segment.mean() if segment.size else 0.0
    return out


@dataclass(frozen=True, slots=True)
class WordMeasures:
    pairing: Pairing
    values: dict[Measure, FloatArray]


def measure_words(participant: Recording, baseline: Recording) -> WordMeasures:
    pairing = pair_words(participant.alignment, baseline.alignment)
    pw, bw = participant.alignment.words, baseline.alignment.words
    n = len(pw)

    cadence = np.full(n, math.nan)
    pitch_var = np.full(n, math.nan)
    pv_p = word_means(participant, FeatureName.PITCH_VARIATION)
    pv_b = word_means(baseline, FeatureName.PITCH_VARIATION)
    for i, j in pairing.index.items():
        length_p = max(pw[i].end - pw[i].start, MIN_WORD_S)
        length_b = max(bw[j].end - bw[j].start, MIN_WORD_S)
        cadence[i] = math.log(length_b / length_p)
        pitch_var[i] = pv_b[j] - pv_p[i]

    rel_p, tail_p, _ = _sentence_levels(participant)
    rel_b, _, _ = _sentence_levels(baseline)
    energy_drop = np.zeros(n)
    for i, j in pairing.index.items():
        if tail_p[i] and not (math.isnan(rel_p[i]) or math.isnan(rel_b[j])):
            energy_drop[i] = rel_b[j] - rel_p[i]

    excess = np.zeros(n)
    deficit = np.zeros(n)
    for i in range(n - 1):
        j = pairing.index.get(i)
        if j is None or pairing.index.get(i + 1) != j + 1:
            continue
        gap_p = gap_after(participant.alignment, i)
        gap_b = gap_after(baseline.alignment, j)
        text = bw[j].text
        if not _ANY_PUNCT.search(text):
            value = max(gap_p - gap_b, 0.0)
            excess[i] = max(excess[i], value)
            excess[i + 1] = max(excess[i + 1], value)
        elif _SENTENCE_END.search(text) and gap_b >= SENTENCE_PAUSE_MIN_S:
            share = float(np.clip(1.0 - gap_p / gap_b, 0.0, 1.0))
            deficit[i] = max(deficit[i], share)
            deficit[i + 1] = max(deficit[i + 1], share)

    return WordMeasures(
        pairing=pairing,
        values={
            Measure.CADENCE: _smooth(_centre(cadence)),
            Measure.PITCH_VARIATION: _smooth(_centre(pitch_var)),
            Measure.GAP_EXCESS: excess,
            Measure.GAP_DEFICIT: deficit,
            Measure.ENERGY_DROP: energy_drop,
        },
    )


@dataclass(frozen=True, slots=True)
class Window:
    start: float
    end: float
    stats: dict[Stat, float]
    """Only statistics that are defined in this window."""


def window_stats(rec: Recording) -> tuple[Window, ...]:
    duration = rec.features.duration_s
    words = rec.alignment.words
    pauses = track(rec.features, FeatureName.PAUSE)
    variation = track(rec.features, FeatureName.PITCH_VARIATION)
    _, _, drops = _sentence_levels(rec)
    starts = np.arange(0.0, max(duration - WINDOW_S, 0.0) + 1e-9, WINDOW_HOP_S)
    windows: list[Window] = []
    for start in starts:
        end = min(start + WINDOW_S, duration)
        stats: dict[Stat, float] = {}
        inside = [w for w in words if start <= (w.start + w.end) / 2 < end]
        stats[Stat.RATE] = len(inside) / (end - start)
        for stat, values in ((Stat.PAUSE_FRACTION, pauses), (Stat.PITCH_VARIATION, variation)):
            value = mean_over(values, start, end)
            if not math.isnan(value):
                stats[stat] = value
        local = [drop for when, drop in drops if start <= when < end]
        if local:
            stats[Stat.ENERGY_DROP] = float(np.mean(local))
        windows.append(Window(start=float(start), end=float(end), stats=stats))
    return tuple(windows)
