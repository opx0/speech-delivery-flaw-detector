"""Find the flaw regions in a participant's reading and score the four delivery axes.

Contrast mode pairs the reading with a gold reading of the same text. Normative mode has no
baseline and slides windows over the reading, flagging those outside the learned bands.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from ..contract import (
    FEATURE_SPECS,
    FLAW_SPECS,
    AxisScore,
    BandReference,
    BaselineReference,
    Deviation,
    FeatureName,
    FlawKind,
    FlawRegion,
    OverlaySeries,
    RubricWeights,
    WordSpan,
)
from ..contract.report import BandExpected, BandSeries, BaselineExpected, BaselineSeries, WarpAnchor
from .calibration import Calibration, Measure, Stat
from .constants import HOP_S, MIN_REGION_S, OVERLAY_HOP_S
from .evidence import (
    FloatArray,
    Window,
    gap_after,
    measure_words,
    track,
    window_stats,
    word_means,
)
from .explain import Finding, explain
from .recording import Recording
from .scoring import Burden, axis_scores, overall, residual, severity

OVERLAY_FEATURES = (
    FeatureName.PITCH,
    FeatureName.PITCH_VARIATION,
    FeatureName.SPEECH_RATE,
    FeatureName.ENERGY,
    FeatureName.PAUSE,
)
BAND_OVERLAY = {
    FeatureName.SPEECH_RATE: Stat.RATE,
    FeatureName.PITCH_VARIATION: Stat.PITCH_VARIATION,
    FeatureName.PAUSE: Stat.PAUSE_FRACTION,
}
KIND_MEASURE: dict[FlawKind, tuple[Measure, float]] = {
    FlawKind.RUSH: (Measure.CADENCE, 1.0),
    FlawKind.DRAG: (Measure.CADENCE, -1.0),
    FlawKind.MONOTONE: (Measure.PITCH_VARIATION, 1.0),
    FlawKind.HESITATION: (Measure.GAP_EXCESS, 1.0),
    FlawKind.PAUSE_COLLAPSE: (Measure.GAP_DEFICIT, 1.0),
    FlawKind.ENERGY_FADE: (Measure.ENERGY_DROP, 1.0),
}
BAND_STAT: dict[FlawKind, tuple[Stat, float]] = {
    FlawKind.RUSH: (Stat.RATE, 1.0),
    FlawKind.DRAG: (Stat.RATE, -1.0),
    FlawKind.MONOTONE: (Stat.PITCH_VARIATION, -1.0),
    FlawKind.HESITATION: (Stat.PAUSE_FRACTION, 1.0),
    FlawKind.PAUSE_COLLAPSE: (Stat.PAUSE_FRACTION, -1.0),
    FlawKind.ENERGY_FADE: (Stat.ENERGY_DROP, 1.0),
}
MERGE_GAP_WORDS = 1


@dataclass(frozen=True, slots=True)
class Findings:
    regions: tuple[FlawRegion, ...]
    axis_scores: tuple[AxisScore, ...]
    overall: float
    overlay: tuple[OverlaySeries, ...]
    reference: BaselineReference | BandReference


GROW_SHARE = 0.5


def _runs(z: FloatArray, threshold: float) -> list[tuple[int, int]]:
    """Regions seeded where evidence reaches `threshold` and grown to neighbouring words that
    reach `GROW_SHARE` of it. Runs separated by at most `MERGE_GAP_WORDS` words are joined."""
    runs: list[list[int]] = []
    for k in np.flatnonzero(z >= GROW_SHARE * threshold):
        if runs and k - runs[-1][1] <= MERGE_GAP_WORDS + 1:
            runs[-1][1] = int(k)
        else:
            runs.append([int(k), int(k)])
    return [(a, b) for a, b in runs if np.any(z[a : b + 1] >= threshold)]


def _silence_share(rec: Recording, first: int, last: int) -> float:
    words = rec.alignment.words
    span = words[last].end - words[first].start
    gaps = sum(gap_after(rec.alignment, k) for k in range(first, last))
    return gaps / span if span > 0 else 0.0


def _region(
    index: int,
    kind: FlawKind,
    first: int,
    last: int,
    z: FloatArray,
    participant: Recording,
    expected: BaselineExpected | BandExpected,
    observed: float,
    quote_baseline: bool,
    calibration: Calibration,
) -> FlawRegion:
    words = participant.alignment
    spec = FLAW_SPECS[kind]
    start, end = words.words[first].start, words.words[last].end
    z_mean = float(np.mean(z[first : last + 1]))
    unit = FEATURE_SPECS[spec.feature].unit
    anchor = (
        expected.value
        if isinstance(expected, BaselineExpected)
        else (expected.high if observed > expected.high else expected.low)
    )
    span = WordSpan(first=first, last=last)
    finding = Finding(kind, start, end, observed, anchor, z_mean, quote_baseline, unit)
    return FlawRegion(
        id=f"region-{index:03d}",
        kind=kind,
        axis=spec.axis,
        start=start,
        end=end,
        words=span,
        severity=severity(z_mean, calibration.scoring),
        deviation=Deviation(
            feature=spec.feature,
            unit=unit,
            observed=round(observed, 4),
            expected=expected,
            delta=round(observed - anchor, 4),
            z_score=round(z_mean, 3),
        ),
        explanation=explain(finding, words.quote(span)),
    )


def _resample(values: FloatArray, times: FloatArray) -> list[float | None]:
    indices = np.clip(np.round(times / HOP_S).astype(int), 0, len(values) - 1)
    return [None if math.isnan(v) else round(float(v), 3) for v in values[indices]]


def _overlay_times(duration: float) -> FloatArray:
    return np.arange(int(duration / OVERLAY_HOP_S) + 1, dtype=np.float64) * OVERLAY_HOP_S


def _kind_axis_scores(
    regions: Sequence[FlawRegion],
    z_by_kind: dict[FlawKind, FloatArray],
    flagged: dict[FlawKind, NDArray[np.bool_]],
    thresholds: dict[FlawKind, float],
    duration: float,
    weights: RubricWeights,
    calibration: Calibration,
) -> tuple[tuple[AxisScore, ...], float]:
    burdens = [Burden(r.kind, r.severity, r.end - r.start) for r in regions]
    residuals = {
        kind: residual(z_by_kind[kind], thresholds[kind], flagged[kind]) for kind in FlawKind
    }
    scores = axis_scores(burdens, residuals, duration, weights, calibration.scoring)
    return scores, overall(scores)


def compare_to_baseline(
    participant: Recording,
    baseline: Recording,
    text_id: str,
    baseline_clip_id: str,
    calibration: Calibration,
    weights: RubricWeights,
) -> Findings:
    measures = measure_words(participant, baseline)
    pairing = measures.pairing
    n = len(participant.alignment.words)
    pw, bw = participant.alignment.words, baseline.alignment.words
    pv_p = word_means(participant, FeatureName.PITCH_VARIATION)
    pv_b = word_means(baseline, FeatureName.PITCH_VARIATION)
    en_p = word_means(participant, FeatureName.ENERGY)
    en_b = word_means(baseline, FeatureName.ENERGY)

    z_by_kind: dict[FlawKind, FloatArray] = {}
    flagged: dict[FlawKind, NDArray[np.bool_]] = {}
    thresholds: dict[FlawKind, float] = {}
    regions: list[FlawRegion] = []
    for kind in FlawKind:
        measure, sign = KIND_MEASURE[kind]
        z = sign * measures.values[measure] / calibration.sigmas.of(measure)
        threshold = calibration.thresholds.of(kind)
        z_by_kind[kind], thresholds[kind] = z, threshold
        flagged[kind] = np.zeros(n, dtype=bool)
        for first, last in _runs(z, threshold):
            if pw[last].end - pw[first].start < MIN_REGION_S:
                continue
            matched = [pairing.index[k] for k in range(first, last + 1) if k in pairing.index]
            if not matched:
                continue
            b_first, b_last = min(matched), max(matched)
            n_words = last - first + 1
            span_p = pw[last].end - pw[first].start
            span_b = bw[b_last].end - bw[b_first].start
            if kind in (FlawKind.RUSH, FlawKind.DRAG):
                observed, exp = n_words / span_p, (b_last - b_first + 1) / span_b
            elif kind is FlawKind.MONOTONE:
                observed = float(np.nanmean(pv_p[first : last + 1]))
                exp = float(np.nanmean(pv_b[b_first : b_last + 1]))
            elif kind in (FlawKind.HESITATION, FlawKind.PAUSE_COLLAPSE):
                observed = _silence_share(participant, first, last)
                exp = _silence_share(baseline, b_first, b_last)
            else:
                observed = float(np.nanmean(en_p[first : last + 1]))
                exp = float(np.nanmean(en_b[b_first : b_last + 1]))
            if math.isnan(observed) or math.isnan(exp):
                continue
            flagged[kind][first : last + 1] = True
            regions.append(
                _region(
                    0,
                    kind,
                    first,
                    last,
                    z,
                    participant,
                    BaselineExpected(value=round(exp, 4)),
                    observed,
                    True,
                    calibration,
                )
            )

    regions = _number(regions)
    scores, total = _kind_axis_scores(
        regions,
        z_by_kind,
        flagged,
        thresholds,
        participant.features.duration_s,
        weights,
        calibration,
    )
    times = _overlay_times(participant.features.duration_s)
    mapped = pairing.warp_times(times)
    overlay = tuple(
        OverlaySeries(
            feature=name,
            hop_s=OVERLAY_HOP_S,
            participant=tuple(_resample(track(participant.features, name), times)),
            expected=BaselineSeries(
                values=tuple(_resample(track(baseline.features, name), mapped))
            ),
        )
        for name in OVERLAY_FEATURES
    )
    reference = BaselineReference(
        clip_id=baseline_clip_id, text_id=text_id, warp=_thin(pairing.warp)
    )
    return Findings(tuple(regions), scores, total, overlay, reference)


def _thin(anchors: tuple[WarpAnchor, ...], limit: int = 200) -> tuple[WarpAnchor, ...]:
    """Keep the report small. Every k-th anchor plus both ends keeps the map monotone."""
    if len(anchors) <= limit:
        return anchors
    step = len(anchors) // limit + 1
    kept = list(anchors[::step])
    if kept[-1] is not anchors[-1]:
        kept.append(anchors[-1])
    return tuple(kept)


def _number(regions: list[FlawRegion]) -> list[FlawRegion]:
    ordered = sorted(regions, key=lambda r: (r.start, r.kind.value))
    return [r.model_copy(update={"id": f"region-{i + 1:03d}"}) for i, r in enumerate(ordered)]


def _window_evidence(
    windows: Sequence[Window], kind: FlawKind, calibration: Calibration
) -> tuple[FloatArray, FloatArray]:
    stat, sign = BAND_STAT[kind]
    band = calibration.bands.of(stat)
    z = np.zeros(len(windows))
    value = np.full(len(windows), math.nan)
    for k, window in enumerate(windows):
        if stat in window.stats:
            value[k] = window.stats[stat]
            outside = sign * (window.stats[stat] - (band.high if sign > 0 else band.low))
            z[k] = max(outside, 0.0) / band.half_width
    return z, value


def compare_to_bands(
    participant: Recording, calibration: Calibration, weights: RubricWeights
) -> Findings:
    words = participant.alignment.words
    windows = window_stats(participant)
    z_by_kind: dict[FlawKind, FloatArray] = {}
    flagged: dict[FlawKind, NDArray[np.bool_]] = {}
    thresholds: dict[FlawKind, float] = {}
    regions: list[FlawRegion] = []
    for kind in FlawKind:
        stat, _ = BAND_STAT[kind]
        band = calibration.bands.of(stat)
        z_windows, values = _window_evidence(windows, kind, calibration)
        threshold = calibration.band_thresholds.of(kind)
        word_z = np.zeros(len(words))
        for k, window in enumerate(windows):
            for w, word in enumerate(words):
                if window.start <= (word.start + word.end) / 2 < window.end:
                    word_z[w] = max(word_z[w], z_windows[k])
        z_by_kind[kind], thresholds[kind] = word_z, threshold
        flagged[kind] = np.zeros(len(words), dtype=bool)
        for first, last in _runs(word_z, threshold):
            if words[last].end - words[first].start < MIN_REGION_S:
                continue
            idx = [
                k
                for k, wd in enumerate(windows)
                if wd.start < words[last].end
                and wd.end > words[first].start
                and not math.isnan(values[k])
            ]
            if not idx:
                continue
            observed = float(np.mean(values[idx]))
            flagged[kind][first : last + 1] = True
            regions.append(
                _region(
                    0,
                    kind,
                    first,
                    last,
                    word_z,
                    participant,
                    BandExpected(low=round(band.low, 4), high=round(band.high, 4)),
                    observed,
                    False,
                    calibration,
                )
            )
    regions = _number(regions)
    scores, total = _kind_axis_scores(
        regions,
        z_by_kind,
        flagged,
        thresholds,
        participant.features.duration_s,
        weights,
        calibration,
    )
    times = _overlay_times(participant.features.duration_s)
    overlay: list[OverlaySeries] = []
    for name in OVERLAY_FEATURES:
        stat = BAND_OVERLAY.get(name)
        if stat is None:
            continue
        band = calibration.bands.of(stat)
        overlay.append(
            OverlaySeries(
                feature=name,
                hop_s=OVERLAY_HOP_S,
                participant=tuple(_resample(track(participant.features, name), times)),
                expected=BandSeries(
                    low=tuple(round(band.low, 4) for _ in times),
                    high=tuple(round(band.high, 4) for _ in times),
                ),
            )
        )
    reference = BandReference(
        n_reference_clips=calibration.n_reference_clips, bands_version=calibration.bands_version
    )
    return Findings(tuple(regions), scores, total, tuple(overlay), reference)
