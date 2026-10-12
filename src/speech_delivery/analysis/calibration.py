"""What the comparison needs to know about normal variation, learned from reference readings.

A contrast z-score divides a gap by how much two good readers of the same text normally differ.
`build_calibration` measures that from natural-reader clips paired with their gold clip. The
normative mode needs p10 to p90 bands, learned from every gold, natural-reader and
normative-reference clip.

Only the calibration split of the library may be used. Human clips and the test split are refused,
so no number the evaluation reports was tuned on the data it is scored on.

Every number below is a placeholder until the real dataset is calibrated. A calibration is
sealed: `version` is the sha256 of the rest of the content, so two analyses can prove they used
the same numbers.
"""

import hashlib
import json
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from ..contract import FlawKind
from ..contract.dataset import HUMAN_ROLES, ClipRole, Split
from ..contract.units import ContractModel, Sha256
from ..library import Library
from .recording import Recording
from .scoring import Scoring


class CalibrationError(ValueError):
    """The reference recordings cannot be used to calibrate."""


class Measure(StrEnum):
    """A per-frame gap between participant and baseline. Positive means the flaw direction."""

    CADENCE = "cadence"
    """Log of baseline word length over participant word length. Positive is faster."""
    PITCH_VARIATION = "pitch_variation"
    """Baseline minus participant pitch variation, in semitones."""
    GAP_EXCESS = "gap_excess"
    """Participant minus baseline silence inside a phrase, in seconds."""
    GAP_DEFICIT = "gap_deficit"
    """Share of the baseline's sentence-end pause that the participant did not leave."""
    ENERGY_DROP = "energy_drop"
    """Baseline minus participant level in the sentence tail, both relative to the sentence."""


class Stat(StrEnum):
    """A statistic of a stretch of speech that has a normative band."""

    RATE = "rate"
    PAUSE_FRACTION = "pause_fraction"
    PITCH_VARIATION = "pitch_variation"
    ENERGY_DROP = "energy_drop"


SIGMA_FLOORS: dict[Measure, float] = {
    Measure.CADENCE: 0.12,
    Measure.PITCH_VARIATION: 0.5,
    Measure.GAP_EXCESS: 0.1,
    Measure.GAP_DEFICIT: 0.2,
    Measure.ENERGY_DROP: 1.5,
}
"""Smallest spread a calibration may report. A reference set with no variance must not make every
small difference look huge."""

CONTRAST_Z_FLOOR = 2.0
"""A contrast threshold is never lower than two reference spreads."""
BAND_Z_FLOOR = 0.5
"""A normative window must lie at least half a band half-width outside the band to count."""
BAND_MIN_WIDTH: dict[Stat, float] = {
    Stat.RATE: 0.6,
    Stat.PAUSE_FRACTION: 0.08,
    Stat.PITCH_VARIATION: 0.8,
    Stat.ENERGY_DROP: 1.0,
}
"""Narrowest p10 to p90 band, in the statistic's own unit."""

_CONTRAST_MARGIN = 0.5
_BAND_MARGIN = 0.25
_QUANTILE = 99.0


class Sigmas(ContractModel):
    cadence: float = Field(default=0.15, gt=0, allow_inf_nan=False)
    pitch_variation: float = Field(default=0.8, gt=0, allow_inf_nan=False)
    gap_excess: float = Field(default=0.15, gt=0, allow_inf_nan=False)
    gap_deficit: float = Field(default=0.3, gt=0, allow_inf_nan=False)
    energy_drop: float = Field(default=2.0, gt=0, allow_inf_nan=False)

    def of(self, measure: Measure) -> float:
        return getattr(self, measure.value)


class KindThresholds(ContractModel):
    """One evidence threshold per flaw kind, in reference spreads (contrast) or half-widths."""

    rush: float = Field(default=2.0, gt=0, allow_inf_nan=False)
    drag: float = Field(default=2.0, gt=0, allow_inf_nan=False)
    monotone: float = Field(default=2.0, gt=0, allow_inf_nan=False)
    hesitation: float = Field(default=2.0, gt=0, allow_inf_nan=False)
    pause_collapse: float = Field(default=2.0, gt=0, allow_inf_nan=False)
    energy_fade: float = Field(default=2.0, gt=0, allow_inf_nan=False)

    def of(self, kind: FlawKind) -> float:
        return getattr(self, kind.value)


class Band(ContractModel):
    low: float = Field(allow_inf_nan=False)
    high: float = Field(allow_inf_nan=False)

    @model_validator(mode="after")
    def _ordered(self) -> "Band":
        if self.high <= self.low:
            raise ValueError("band high must exceed band low")
        return self

    @property
    def half_width(self) -> float:
        return (self.high - self.low) / 2


class Bands(ContractModel):
    rate: Band = Band(low=2.4, high=4.0)
    pause_fraction: Band = Band(low=0.03, high=0.40)
    pitch_variation: Band = Band(low=1.2, high=3.8)
    energy_drop: Band = Band(low=-1.5, high=5.0)

    def of(self, stat: Stat) -> Band:
        return getattr(self, stat.value)


class Calibration(ContractModel):
    """Frozen, validated and sealed. Build one with `seal`, `build_calibration` or the default."""

    version: Sha256
    sigmas: Sigmas
    thresholds: KindThresholds
    bands: Bands
    band_thresholds: KindThresholds
    n_reference_clips: int = Field(ge=1)
    n_calibration_pairs: int = Field(ge=0)
    scoring: Scoring

    @model_validator(mode="after")
    def _sealed_and_above_floors(self) -> "Calibration":
        for measure, floor in SIGMA_FLOORS.items():
            if self.sigmas.of(measure) < floor:
                raise ValueError(f"{measure.value} spread is below its floor of {floor}")
        for kind in FlawKind:
            if self.thresholds.of(kind) < CONTRAST_Z_FLOOR:
                raise ValueError(f"{kind.value} threshold is below {CONTRAST_Z_FLOOR}")
            if self.band_thresholds.of(kind) < BAND_Z_FLOOR:
                raise ValueError(f"{kind.value} band threshold is below {BAND_Z_FLOOR}")
        if self.version != _digest(self.model_dump(mode="json", exclude={"version"})):
            raise ValueError("calibration version does not match its content")
        return self

    @property
    def bands_version(self) -> str:
        content = {"bands": self.bands, "thresholds": self.band_thresholds}
        return _digest(_jsonable(content))[:12]


def _jsonable(content: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value.model_dump(mode="json") if isinstance(value, ContractModel) else value
        for key, value in content.items()
    }


def _digest(content: Mapping[str, Any]) -> str:
    text = json.dumps(content, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def seal(
    *,
    sigmas: Sigmas,
    thresholds: KindThresholds,
    bands: Bands,
    band_thresholds: KindThresholds,
    n_reference_clips: int,
    n_calibration_pairs: int,
    scoring: Scoring,
) -> Calibration:
    draft = Calibration.model_construct(
        version="",
        sigmas=sigmas,
        thresholds=thresholds,
        bands=bands,
        band_thresholds=band_thresholds,
        n_reference_clips=n_reference_clips,
        n_calibration_pairs=n_calibration_pairs,
        scoring=scoring,
    )
    version = _digest(draft.model_dump(mode="json", exclude={"version"}))
    return Calibration(
        version=version,
        sigmas=sigmas,
        thresholds=thresholds,
        bands=bands,
        band_thresholds=band_thresholds,
        n_reference_clips=n_reference_clips,
        n_calibration_pairs=n_calibration_pairs,
        scoring=scoring,
    )


def default_calibration() -> Calibration:
    """Placeholder numbers, for tests and for a first run before a dataset exists."""
    return seal(
        sigmas=Sigmas(),
        thresholds=KindThresholds(),
        bands=Bands(),
        band_thresholds=KindThresholds(
            rush=1.0, drag=1.0, monotone=1.0, hesitation=1.0, pause_collapse=1.0, energy_fade=1.0
        ),
        n_reference_clips=1,
        n_calibration_pairs=0,
        scoring=Scoring(),
    )


def reject_unusable(library: Library, clip_ids: Mapping[str, Recording]) -> None:
    """Refuse human clips and the test split, so nothing scored later was tuned on it."""
    for clip_id in clip_ids:
        clip = library.clip(clip_id)
        if clip.role in HUMAN_ROLES:
            raise CalibrationError(f"{clip_id} is a human recording, it is held out for testing")
        if clip.split is not Split.CALIBRATION:
            raise CalibrationError(f"{clip_id} is in the test split")
        if clip.role not in _CALIBRATION_ROLES:
            raise CalibrationError(f"{clip_id} has role {clip.role.value}, not a reference")


_CALIBRATION_ROLES = frozenset(
    {ClipRole.GOLD, ClipRole.NATURAL_READER, ClipRole.NORMATIVE_REFERENCE}
)


def save_calibration(calibration: Calibration, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(calibration.model_dump(mode="json"), sort_keys=True, indent=2)
    path.write_text(text + "\n", encoding="utf-8")


def load_calibration(path: Path) -> Calibration:
    return Calibration.model_validate_json(path.read_text(encoding="utf-8"))
