"""Learn the comparison's spreads, thresholds and normative bands from reference readings.

A contrast spread is how much two good readers of the same text normally differ on a measure.
A threshold is the highest evidence those good-reader pairs produced, so a different speaker's
normal phrasing is not flagged. Bands are the p10 to p90 range of windowed statistics over every
reference reading.
"""

from collections.abc import Mapping

import numpy as np
from numpy.typing import NDArray

from ..contract import FlawKind
from ..contract.dataset import ClipRole
from ..library import Library
from .calibration import (
    BAND_MIN_WIDTH,
    CONTRAST_Z_FLOOR,
    SIGMA_FLOORS,
    Band,
    Bands,
    Calibration,
    CalibrationError,
    KindThresholds,
    Measure,
    Sigmas,
    Stat,
    default_calibration,
    reject_unusable,
    seal,
)
from .compare import KIND_MEASURE
from .evidence import measure_words, window_stats
from .recording import Recording
from .scoring import Scoring

BAND_QUANTILES = (10.0, 90.0)
BAND_MARGIN = 0.25
CONTRAST_MARGIN = 0.03


def build_calibration(library: Library, recordings: Mapping[str, Recording]) -> Calibration:
    """Calibrate from gold, natural-reader and normative-reference recordings keyed by clip id."""
    reject_unusable(library, recordings)
    pairs: list[dict[Measure, NDArray[np.float64]]] = []
    for clip_id, recording in recordings.items():
        clip = library.clip(clip_id)
        baseline_id = clip.baseline_clip_id
        if clip.role is not ClipRole.NATURAL_READER or baseline_id not in recordings:
            continue
        assert baseline_id is not None
        measures = measure_words(recording, recordings[baseline_id])
        pairs.append(measures.values)
    if not pairs:
        raise CalibrationError("no natural-reader pair is available to measure normal variation")

    sigmas: dict[Measure, float] = {}
    for measure, floor in SIGMA_FLOORS.items():
        values = np.concatenate([p[measure] for p in pairs])
        sigmas[measure] = max(float(np.std(values)), floor)

    thresholds: dict[FlawKind, float] = {}
    for kind in FlawKind:
        measure, sign = KIND_MEASURE[kind]
        evidence = np.concatenate([sign * p[measure] / sigmas[measure] for p in pairs])
        # One word reaching the threshold seeds a region, so the threshold must clear the highest
        # evidence any reference pair produced, not a percentile of it.
        high = float(np.max(evidence)) * (1.0 + CONTRAST_MARGIN)
        thresholds[kind] = max(high, CONTRAST_Z_FLOOR)

    return seal(
        sigmas=Sigmas(**{m.value: v for m, v in sigmas.items()}),
        thresholds=KindThresholds(**{k.value: v for k, v in thresholds.items()}),
        bands=_bands(recordings),
        band_thresholds=default_calibration().band_thresholds,
        n_reference_clips=len(recordings),
        n_calibration_pairs=len(pairs),
        scoring=Scoring(),
    )


def _bands(recordings: Mapping[str, Recording]) -> Bands:
    collected: dict[Stat, list[float]] = {stat: [] for stat in Stat}
    for recording in recordings.values():
        for window in window_stats(recording):
            for stat, value in window.stats.items():
                collected[stat].append(value)
    bands: dict[str, Band] = {}
    defaults = Bands()
    for stat in Stat:
        values = collected[stat]
        if len(values) < 10:
            bands[stat.value] = defaults.of(stat)
            continue
        low, high = np.percentile(values, BAND_QUANTILES)
        margin = BAND_MARGIN * (high - low)
        low, high = float(low - margin), float(high + margin)
        width = BAND_MIN_WIDTH[stat]
        if high - low < width:
            mid = (high + low) / 2
            low, high = mid - width / 2, mid + width / 2
        bands[stat.value] = Band(low=low, high=high)
    return Bands(**bands)
