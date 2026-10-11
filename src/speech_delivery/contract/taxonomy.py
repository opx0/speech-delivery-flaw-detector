"""The delivery taxonomy: axes, flaw kinds, and the feature each flaw is judged by.

`FLAW_SPECS` is the one table that injection, detection and explanation all read, so a
flaw kind cannot mean different things in different packages.
"""

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType


class Axis(StrEnum):
    """The four delivery axes a judge scores."""

    CADENCE = "cadence"
    TONE = "tone"
    PAUSES = "pauses"
    VOLUME = "volume"


class FeatureName(StrEnum):
    """Time-series features rendered in the overlay and used as flaw evidence."""

    SPEECH_RATE = "speech_rate"
    PITCH = "pitch"
    PITCH_VARIATION = "pitch_variation"
    ENERGY = "energy"
    PAUSE = "pause"
    CLARITY = "clarity"


class FlawKind(StrEnum):
    RUSH = "rush"
    DRAG = "drag"
    MONOTONE = "monotone"
    HESITATION = "hesitation"
    PAUSE_COLLAPSE = "pause_collapse"
    ENERGY_FADE = "energy_fade"


class Direction(StrEnum):
    """Which way the observed feature departs from what is expected."""

    ABOVE = "above"
    BELOW = "below"


@dataclass(frozen=True, slots=True)
class FeatureSpec:
    unit: str
    label: str


@dataclass(frozen=True, slots=True)
class FlawSpec:
    axis: Axis
    feature: FeatureName
    direction: Direction
    label: str


FEATURE_SPECS = MappingProxyType(
    {
        FeatureName.SPEECH_RATE: FeatureSpec(unit="words/s", label="Speech rate"),
        FeatureName.PITCH: FeatureSpec(unit="semitones", label="Pitch"),
        FeatureName.PITCH_VARIATION: FeatureSpec(unit="semitones", label="Pitch variation"),
        FeatureName.ENERGY: FeatureSpec(unit="dB", label="Vocal energy"),
        FeatureName.PAUSE: FeatureSpec(unit="fraction silent", label="Silence"),
        FeatureName.CLARITY: FeatureSpec(unit="dB", label="Vocal clarity"),
    }
)

FLAW_SPECS = MappingProxyType(
    {
        FlawKind.RUSH: FlawSpec(
            Axis.CADENCE, FeatureName.SPEECH_RATE, Direction.ABOVE, "Rushed pacing"
        ),
        FlawKind.DRAG: FlawSpec(
            Axis.CADENCE, FeatureName.SPEECH_RATE, Direction.BELOW, "Dragging pace"
        ),
        FlawKind.MONOTONE: FlawSpec(
            Axis.TONE, FeatureName.PITCH_VARIATION, Direction.BELOW, "Monotone pitch"
        ),
        FlawKind.HESITATION: FlawSpec(
            Axis.PAUSES, FeatureName.PAUSE, Direction.ABOVE, "Hesitation mid-phrase"
        ),
        FlawKind.PAUSE_COLLAPSE: FlawSpec(
            Axis.PAUSES, FeatureName.PAUSE, Direction.BELOW, "Missing dramatic pause"
        ),
        FlawKind.ENERGY_FADE: FlawSpec(
            Axis.VOLUME, FeatureName.ENERGY, Direction.BELOW, "Fading energy"
        ),
    }
)

assert set(FLAW_SPECS) == set(FlawKind), "every flaw kind needs a spec"
assert set(FEATURE_SPECS) == set(FeatureName), "every feature needs a spec"
