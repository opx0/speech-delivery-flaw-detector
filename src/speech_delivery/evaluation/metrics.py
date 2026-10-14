"""Pure scoring functions for the evaluation. No audio, no models: regions in, numbers out."""

from collections.abc import Sequence
from dataclasses import dataclass
from math import sqrt
from statistics import median
from typing import Any

from scipy.stats import spearmanr

from ..contract import FlawKind

IOU_HIT = 0.5
IOU_TYPE = 0.3


def binomial_interval(successes: int, trials: int) -> tuple[float, float] | None:
    """95% Wilson interval for a proportion, assuming independent Bernoulli trials.

    Correlated regions from one speaker are not independent. This interval is descriptive,
    not evidence of population-wide speaker generalization.
    """
    if trials < 0 or not 0 <= successes <= trials:
        raise ValueError("successes must be between zero and the nonnegative trial count")
    if trials == 0:
        return None
    z = 1.959963984540054
    proportion = successes / trials
    denominator = 1.0 + z * z / trials
    centre = (proportion + z * z / (2.0 * trials)) / denominator
    radius = (
        z
        * sqrt(proportion * (1.0 - proportion) / trials + z * z / (4.0 * trials * trials))
        / denominator
    )
    return max(0.0, centre - radius), min(1.0, centre + radius)


@dataclass(frozen=True, slots=True)
class Span:
    kind: FlawKind
    start: float
    end: float


def iou(a: Span, b: Span) -> float:
    inter = max(0.0, min(a.end, b.end) - max(a.start, b.start))
    union = (a.end - a.start) + (b.end - b.start) - inter
    return inter / union if union > 0 else 0.0


@dataclass(frozen=True, slots=True)
class Matching:
    pairs: tuple[tuple[Span, Span], ...]
    """(truth, predicted) pairs of the same kind, each span used once."""
    truth: int
    predicted: int


def match(truth: Sequence[Span], predicted: Sequence[Span], threshold: float = IOU_HIT) -> Matching:
    """Greedy one-to-one matching of same-kind spans by descending IoU."""
    candidates = sorted(
        (
            (iou(t, p), i, j)
            for i, t in enumerate(truth)
            for j, p in enumerate(predicted)
            if t.kind is p.kind
        ),
        reverse=True,
    )
    used_t: set[int] = set()
    used_p: set[int] = set()
    pairs: list[tuple[Span, Span]] = []
    for score, i, j in candidates:
        if score < threshold:
            break
        if i in used_t or j in used_p:
            continue
        used_t.add(i)
        used_p.add(j)
        pairs.append((truth[i], predicted[j]))
    return Matching(tuple(pairs), len(truth), len(predicted))


def precision_recall(matches: Sequence[Matching]) -> tuple[float, float]:
    hits = sum(len(m.pairs) for m in matches)
    predicted = sum(m.predicted for m in matches)
    truth = sum(m.truth for m in matches)
    return (hits / predicted if predicted else 1.0, hits / truth if truth else 1.0)


def median_boundary_error_ms(matches: Sequence[Matching]) -> float | None:
    errors = [
        abs(edge) * 1000
        for m in matches
        for t, p in m.pairs
        for edge in (p.start - t.start, p.end - t.end)
    ]
    return median(errors) if errors else None


def type_accuracy(truth: Sequence[Span], predicted: Sequence[Span]) -> tuple[int, int]:
    """Of the true flaws that something overlaps, how many were given the right kind.

    Returns (right, located). A flaw nothing overlaps is a miss for recall, not a typing error.
    """
    right = located = 0
    for t in truth:
        best = max(predicted, key=lambda p: iou(t, p), default=None)
        if best is None or iou(t, best) < IOU_TYPE:
            continue
        located += 1
        right += best.kind is t.kind
    return right, located


def severity_spearman(scores_by_level: Sequence[float]) -> float:
    """Rank correlation between severity level (0 to 4) and the axis score. Perfect is -1."""
    if len(scores_by_level) < 3 or len(set(scores_by_level)) == 1:
        return 0.0
    result: Any = spearmanr(range(len(scores_by_level)), scores_by_level)
    return float(result.statistic)
