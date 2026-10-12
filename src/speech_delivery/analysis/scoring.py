"""Severity and axis scores, defined once.

Severity of one region is `1 - exp(-z / severity_scale_z)`, where z is the region's mean evidence
in the reference's own variability. It rises with z and saturates at 1.

An axis score is `100 * exp(-(burden_gain * burden + residual_gain * residual))`.

- `burden` is the sum over the axis's regions of severity times seconds, over the clip length.
- `residual` is the mean over the clip's words of the squared evidence share
  `min(z / threshold, 1)` taken outside flagged regions, so a reading that stays under every
  threshold but leans the wrong way still scores a little below a perfect copy of the baseline.

Both terms only grow with severity and flagged time, so the score only falls. A reading identical to
its baseline has no evidence and scores exactly 100. Crossing a threshold must never raise the
score, which holds while `burden_gain * severity(threshold) > residual_gain`. With the defaults
that is 4.0 * 0.39 > 1.0.
"""

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from ..contract import FLAW_SPECS, Axis, AxisScore, FlawKind, RubricWeights
from ..contract.units import ContractModel


class Scoring(ContractModel):
    """Every tunable number of the scoring formula, carried by `Calibration`."""

    severity_scale_z: float = Field(default=4.0, gt=0, allow_inf_nan=False)
    burden_gain: float = Field(default=4.0, gt=0, allow_inf_nan=False)
    residual_gain: float = Field(default=1.0, ge=0, allow_inf_nan=False)


@dataclass(frozen=True, slots=True)
class Burden:
    """One flagged region as the score sees it. `seconds` is the longer of the two clocks."""

    kind: FlawKind
    severity: float
    seconds: float


def severity(z: float, scoring: Scoring) -> float:
    return 1.0 - math.exp(-max(z, 0.0) / scoring.severity_scale_z)


def residual(z: NDArray[np.float64], threshold: float, flagged: NDArray[np.bool_]) -> float:
    """Mean squared share of the threshold reached by evidence that was not flagged."""
    share = np.clip(np.nan_to_num(z, nan=0.0) / threshold, 0.0, 1.0)
    share[flagged] = 0.0
    return float(np.mean(share**2)) if share.size else 0.0


def axis_scores(
    burdens: Iterable[Burden],
    residuals: Mapping[FlawKind, float],
    clip_s: float,
    weights: RubricWeights,
    scoring: Scoring,
) -> tuple[AxisScore, ...]:
    burden_list = tuple(burdens)
    scores: list[AxisScore] = []
    for axis in Axis:
        kinds = [kind for kind, spec in FLAW_SPECS.items() if spec.axis is axis]
        flagged = sum(b.severity * b.seconds for b in burden_list if b.kind in kinds) / clip_s
        leftover = sum(residuals.get(kind, 0.0) for kind in kinds)
        exponent = scoring.burden_gain * flagged + scoring.residual_gain * leftover
        scores.append(
            AxisScore(axis=axis, score=100.0 * math.exp(-exponent), weight=weights.weight(axis))
        )
    return tuple(scores)


def overall(scores: Iterable[AxisScore]) -> float:
    """The weighted mean exactly as `Report` checks it."""
    return sum(score.score * score.weight for score in scores)
