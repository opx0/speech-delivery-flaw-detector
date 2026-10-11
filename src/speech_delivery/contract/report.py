"""The analysis result the dashboard renders.

A report is either measured against a gold baseline of the same text (`basis == "baseline"`)
or against normative bands (`basis == "band"`). The discriminator is carried by the reference,
every flaw's evidence and every overlay series, and the report validates that they agree, so a
normative finding can never be presented with baseline-level confidence.
"""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from .alignment import WordAlignment, WordSpan
from .rubric import RubricWeights
from .taxonomy import FLAW_SPECS, Axis, FeatureName, FlawKind
from .units import (
    ContractModel,
    FiniteFloat,
    Identifier,
    Score,
    Seconds,
    Sha256,
    UnitInterval,
)

SCORE_TOLERANCE = 1e-6


class WarpAnchor(ContractModel):
    """Participant time `participant_s` lines up with baseline time `baseline_s`."""

    participant_s: Seconds
    baseline_s: Seconds


class BaselineReference(ContractModel):
    basis: Literal["baseline"] = "baseline"
    clip_id: Identifier
    text_id: Identifier
    warp: tuple[WarpAnchor, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def _warp_is_monotone(self) -> "BaselineReference":
        for before, after in zip(self.warp, self.warp[1:], strict=False):
            if after.participant_s < before.participant_s or after.baseline_s < before.baseline_s:
                raise ValueError("warp anchors must be non-decreasing in both clocks")
        return self


class BandReference(ContractModel):
    basis: Literal["band"] = "band"
    n_reference_clips: int = Field(ge=1)
    bands_version: str


Reference = Annotated[BaselineReference | BandReference, Field(discriminator="basis")]


class BaselineExpected(ContractModel):
    basis: Literal["baseline"] = "baseline"
    value: FiniteFloat


class BandExpected(ContractModel):
    basis: Literal["band"] = "band"
    low: FiniteFloat
    high: FiniteFloat

    @model_validator(mode="after")
    def _ordered(self) -> "BandExpected":
        if self.high < self.low:
            raise ValueError("band high is below band low")
        return self


Expected = Annotated[BaselineExpected | BandExpected, Field(discriminator="basis")]


class Deviation(ContractModel):
    """The measured gap behind a flaw.

    `delta` is observed minus the baseline value, or the signed distance outside the nearest
    band edge. `z_score` is that gap in units of the reference's own variability.
    """

    feature: FeatureName
    unit: str
    observed: FiniteFloat
    expected: Expected
    delta: FiniteFloat
    z_score: FiniteFloat


class Explanation(ContractModel):
    headline: str
    detail: str
    quoted_text: str


class FlawRegion(ContractModel):
    id: Identifier
    kind: FlawKind
    axis: Axis
    start: Seconds
    end: Seconds
    words: WordSpan
    severity: UnitInterval
    deviation: Deviation
    explanation: Explanation

    @model_validator(mode="after")
    def _matches_taxonomy(self) -> "FlawRegion":
        spec = FLAW_SPECS[self.kind]
        if self.end <= self.start:
            raise ValueError("flaw region must have positive length")
        if self.axis is not spec.axis:
            raise ValueError(f"{self.kind.value} belongs to the {spec.axis.value} axis")
        if self.deviation.feature is not spec.feature:
            raise ValueError(f"{self.kind.value} is evidenced by {spec.feature.value}")
        return self


class BaselineSeries(ContractModel):
    basis: Literal["baseline"] = "baseline"
    values: tuple[FiniteFloat | None, ...]


class BandSeries(ContractModel):
    basis: Literal["band"] = "band"
    low: tuple[FiniteFloat | None, ...]
    high: tuple[FiniteFloat | None, ...]

    @model_validator(mode="after")
    def _same_length(self) -> "BandSeries":
        if len(self.low) != len(self.high):
            raise ValueError("band edges must have equal length")
        return self


ExpectedSeries = Annotated[BaselineSeries | BandSeries, Field(discriminator="basis")]


class OverlaySeries(ContractModel):
    """One feature on the participant's clock, with what was expected drawn beside it."""

    feature: FeatureName
    hop_s: Seconds = Field(gt=0)
    participant: tuple[FiniteFloat | None, ...]
    expected: ExpectedSeries

    @model_validator(mode="after")
    def _aligned_lengths(self) -> "OverlaySeries":
        expected = self.expected
        expected_length = (
            len(expected.values) if isinstance(expected, BaselineSeries) else len(expected.low)
        )
        if expected_length != len(self.participant):
            raise ValueError("expected series must have one sample per participant sample")
        return self


class AxisScore(ContractModel):
    axis: Axis
    score: Score
    weight: UnitInterval


class ParticipantInfo(ContractModel):
    filename: str
    duration_s: Seconds = Field(gt=0)
    audio_sha256: Sha256


class ModelStamp(ContractModel):
    name: str
    revision: str


class RunStamp(ContractModel):
    """Everything that must match for two runs to produce the identical report."""

    package_version: str
    config_hash: Sha256
    seed: int
    models: tuple[ModelStamp, ...]


class Report(ContractModel):
    schema_version: Literal[1] = 1
    participant: ParticipantInfo
    reference: Reference
    words: WordAlignment
    weights: RubricWeights
    axis_scores: tuple[AxisScore, ...]
    overall: Score
    regions: tuple[FlawRegion, ...]
    overlay: tuple[OverlaySeries, ...]
    run: RunStamp

    @model_validator(mode="after")
    def _coherent(self) -> "Report":
        basis = self.reference.basis
        for region in self.regions:
            if region.deviation.expected.basis != basis:
                raise ValueError(f"region {region.id} was not measured against the {basis}")
            if region.words.last >= len(self.words.words):
                raise ValueError(f"region {region.id} runs past the transcript")
        for series in self.overlay:
            if series.expected.basis != basis:
                raise ValueError(f"overlay {series.feature.value} was not built from the {basis}")
        if sorted(score.axis.value for score in self.axis_scores) != sorted(a.value for a in Axis):
            raise ValueError("report needs exactly one score per axis")
        for score in self.axis_scores:
            if abs(score.weight - self.weights.weight(score.axis)) > SCORE_TOLERANCE:
                raise ValueError(f"{score.axis.value} weight disagrees with the rubric weights")
        weighted = sum(score.score * score.weight for score in self.axis_scores)
        if abs(weighted - self.overall) > SCORE_TOLERANCE:
            raise ValueError("overall score is not the weighted mean of the axis scores")
        return self
