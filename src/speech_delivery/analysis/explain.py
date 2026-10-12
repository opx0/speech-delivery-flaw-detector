"""The words on a flaw card. One template per flaw kind, filled from the measured deviation."""

from collections.abc import Callable
from dataclasses import dataclass

from ..contract import FEATURE_SPECS, FLAW_SPECS, Explanation, FlawKind

SHORT_REGION_S = 2.0


@dataclass(frozen=True, slots=True)
class Finding:
    kind: FlawKind
    start: float
    end: float
    observed: float
    expected: float
    """The baseline value, or in normative mode the nearest band edge."""
    z: float
    baseline: bool
    """True when measured against a gold reading of the same text."""
    unit: str


def clock(seconds: float, *, tenths: bool = False) -> str:
    total = round(seconds * 10) if tenths else int(seconds) * 10
    whole, tenth = divmod(total, 10)
    text = f"{whole // 60:02d}:{whole % 60:02d}"
    return f"{text}.{tenth}" if tenths else text


def _num(value: float, unit: str) -> str:
    if unit == "fraction silent":
        return f"{value * 100:.0f}% silence"
    if unit == "semitones":
        return f"{value:.1f} semitones"
    if unit == "words/s":
        return f"{value:.1f} words/s"
    return f"{value:.1f} {unit}"


def _percent_change(observed: float, expected: float) -> str:
    if expected == 0:
        return ""
    change = (observed - expected) / abs(expected) * 100
    return f"{abs(change):.0f}% {'higher' if change > 0 else 'lower'}"


_REASON: dict[FlawKind, Callable[[Finding], str]] = {
    FlawKind.RUSH: lambda f: (
        f"Speech ran {_percent_change(f.observed, f.expected)} than expected. "
        "A fast stretch gives listeners less time to take in the point and flattens the emphasis."
    ),
    FlawKind.DRAG: lambda f: (
        f"Speech ran {_percent_change(f.observed, f.expected)} than expected. "
        "A slow stretch loses momentum and makes the line sound hesitant."
    ),
    FlawKind.MONOTONE: lambda f: (
        f"Pitch moved only {f.observed:.1f} semitones where {f.expected:.1f} was expected. "
        "A flat voice removes the rise and fall that signals emphasis and feeling."
    ),
    FlawKind.HESITATION: lambda f: (
        f"{_num(f.observed, f.unit)} fell in the middle of a phrase where "
        f"{_num(f.expected, f.unit)} was expected. "
        "A stop inside a phrase breaks the thought and reads as uncertainty."
    ),
    FlawKind.PAUSE_COLLAPSE: lambda f: (
        f"Only {_num(f.observed, f.unit)} was left where {_num(f.expected, f.unit)} was expected. "
        "A pause at a sentence end lets an idea land. Without it the sentences run together."
    ),
    FlawKind.ENERGY_FADE: lambda f: (
        f"The ending sat {abs(f.observed - f.expected):.1f} dB lower than expected "
        "against the rest of its sentence. The key words at the end of a sentence fade out."
    ),
}


def explain(finding: Finding, quote: str) -> Explanation:
    spec = FLAW_SPECS[finding.kind]
    fine = finding.end - finding.start < SHORT_REGION_S
    span = f"{clock(finding.start, tenths=fine)} to {clock(finding.end, tenths=fine)}"
    expected = (
        "an expected"
        if finding.baseline
        else "a typical upper limit of"
        if (finding.kind in (FlawKind.RUSH, FlawKind.HESITATION, FlawKind.ENERGY_FADE))
        else "a typical lower limit of"
    )
    unit = FEATURE_SPECS[spec.feature].unit
    headline = (
        f"{spec.label}, {span}, {_num(finding.observed, unit)} against {expected} "
        f"{_num(finding.expected, unit)}"
    )
    spread = "reference spreads" if finding.baseline else "band half-widths"
    basis = (
        "Measured against the gold reading of the same words."
        if finding.baseline
        else "Measured against typical ranges, not the same text, so confidence is lower."
    )
    detail = (
        f"{_REASON[finding.kind](finding)} "
        f"The gap is {finding.z:.1f} {spread} from what was expected. {basis}"
    )
    return Explanation(headline=headline, detail=detail, quoted_text=quote)
