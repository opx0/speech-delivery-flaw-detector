"""The contrastive dataset: provenance, ground-truth flaw labels, and the manifest tying them.

The manifest checks its own referential integrity, so a loader cannot hand the rest of the
system a clip whose baseline, text or source does not exist.
"""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .alignment import WordAlignment, WordSpan
from .taxonomy import FlawKind
from .units import (
    ContractModel,
    Identifier,
    RelativePosixPath,
    Seconds,
    Sha256,
    UnitInterval,
    WordIndex,
)


class Category(StrEnum):
    """Competition category. Extemporaneous has no fixed text, so it never has a flawed mirror."""

    INTERPRETIVE_READING = "interpretive_reading"
    DECLAMATION = "declamation"
    PERSUASIVE_ORATORY = "persuasive_oratory"
    EXTEMPORANEOUS = "extemporaneous"


class License(StrEnum):
    PUBLIC_DOMAIN_MARK = "public-domain-mark"
    CC0 = "cc0"
    US_GOVERNMENT_WORK = "us-government-work"
    CC_BY_4 = "cc-by-4.0"
    ORIGINAL_RECORDING = "original-recording"


class Sex(StrEnum):
    FEMALE = "female"
    MALE = "male"
    UNSPECIFIED = "unspecified"


class ClipRole(StrEnum):
    GOLD = "gold"
    CONTROL = "control"
    FLAWED = "flawed"
    NATURAL_READER = "natural_reader"
    SPEAKER_SHIFTED = "speaker_shifted"
    HUMAN_CLEAN = "human_clean"
    HUMAN_FLAWED = "human_flawed"
    NORMATIVE_REFERENCE = "normative_reference"


class Split(StrEnum):
    CALIBRATION = "calibration"
    TEST = "test"


HUMAN_ROLES = frozenset({ClipRole.HUMAN_CLEAN, ClipRole.HUMAN_FLAWED})
DSP_ROLES = frozenset({ClipRole.CONTROL, ClipRole.FLAWED, ClipRole.SPEAKER_SHIFTED})
FLAWED_ROLES = frozenset({ClipRole.FLAWED, ClipRole.HUMAN_FLAWED})
ROOT_ROLES = frozenset({ClipRole.GOLD, ClipRole.NORMATIVE_REFERENCE})


class RightsEvidence(ContractModel):
    license: License
    evidence_url: str
    verified: bool
    notes: str


class SourceRecord(ContractModel):
    id: Identifier
    title: str
    speaker_name: str
    speaker_sex: Sex
    page_url: str
    audio_url: str
    excerpt_start: Seconds
    excerpt_end: Seconds
    rights: RightsEvidence

    @model_validator(mode="after")
    def _excerpt_ordered(self) -> "SourceRecord":
        if self.excerpt_end <= self.excerpt_start:
            raise ValueError("excerpt must have positive length")
        return self


class TextRecord(ContractModel):
    id: Identifier
    title: str
    category: Category
    transcript: str
    transcript_url: str


class AudioFile(ContractModel):
    path: RelativePosixPath
    sha256: Sha256
    duration_s: Seconds = Field(gt=0)
    sample_rate_hz: int = Field(gt=0)


class PipelineStamp(ContractModel):
    """How a derived clip was produced, enough to regenerate it byte for byte."""

    name: str
    version: str
    seed: int
    config_hash: Sha256


class RushParams(ContractModel):
    kind: Literal[FlawKind.RUSH] = FlawKind.RUSH
    rate_factor: float = Field(gt=1, allow_inf_nan=False)


class DragParams(ContractModel):
    kind: Literal[FlawKind.DRAG] = FlawKind.DRAG
    rate_factor: float = Field(gt=0, lt=1, allow_inf_nan=False)


class MonotoneParams(ContractModel):
    kind: Literal[FlawKind.MONOTONE] = FlawKind.MONOTONE
    pitch_excursion_retained: UnitInterval


class InsertedSilence(ContractModel):
    after_word: WordIndex
    duration_s: Seconds = Field(gt=0)


class HesitationParams(ContractModel):
    kind: Literal[FlawKind.HESITATION] = FlawKind.HESITATION
    silences: tuple[InsertedSilence, ...] = Field(min_length=1)


class PauseCollapseParams(ContractModel):
    kind: Literal[FlawKind.PAUSE_COLLAPSE] = FlawKind.PAUSE_COLLAPSE
    pause_retained: UnitInterval


class EnergyFadeParams(ContractModel):
    kind: Literal[FlawKind.ENERGY_FADE] = FlawKind.ENERGY_FADE
    drop_db: float = Field(gt=0, allow_inf_nan=False)
    fade_fraction: UnitInterval


InjectionParams = Annotated[
    RushParams
    | DragParams
    | MonotoneParams
    | HesitationParams
    | PauseCollapseParams
    | EnergyFadeParams,
    Field(discriminator="kind"),
]


class FlawLabel(ContractModel):
    """A ground-truth flaw region. `injection` is set for DSP clips and absent for human ones."""

    kind: FlawKind
    level: Literal[1, 2, 3, 4]
    start: Seconds
    end: Seconds
    words: WordSpan
    injection: InjectionParams | None

    @model_validator(mode="after")
    def _consistent(self) -> "FlawLabel":
        if self.end <= self.start:
            raise ValueError("flaw region must have positive length")
        if self.injection is not None and self.injection.kind != self.kind:
            raise ValueError("injection parameters do not match the flaw kind")
        return self


class ClipLabel(ContractModel):
    id: Identifier
    text_id: Identifier
    role: ClipRole
    split: Split
    speaker_sex: Sex
    audio: AudioFile
    alignment: WordAlignment
    baseline_clip_id: Identifier | None
    source_id: Identifier | None
    pipeline: PipelineStamp | None
    flaws: tuple[FlawLabel, ...]

    @model_validator(mode="after")
    def _role_rules(self) -> "ClipLabel":
        role = self.role
        _require(role, role not in ROOT_ROLES, self.baseline_clip_id is not None, "a baseline")
        _require(role, role in DSP_ROLES, self.pipeline is not None, "a pipeline stamp")
        _require(
            role,
            role in ROOT_ROLES or role is ClipRole.NATURAL_READER,
            self.source_id is not None,
            "a source",
        )
        _require(role, role in FLAWED_ROLES, bool(self.flaws), "flaw labels")
        if role in HUMAN_ROLES and self.split is not Split.TEST:
            raise ValueError("human recordings are held out for testing only")
        for flaw in self.flaws:
            if (flaw.injection is None) != (role is ClipRole.HUMAN_FLAWED):
                raise ValueError("only human clips omit injection parameters")
            if flaw.end > self.audio.duration_s + 1e-3:
                raise ValueError("flaw region runs past the end of the audio")
            if flaw.words.last >= len(self.alignment.words):
                raise ValueError("flaw word span runs past the alignment")
        return self


class DatasetManifest(ContractModel):
    schema_version: Literal[1] = 1
    dataset_version: str
    sources: tuple[SourceRecord, ...]
    texts: tuple[TextRecord, ...]
    clips: tuple[ClipLabel, ...]

    @model_validator(mode="after")
    def _references_resolve(self) -> "DatasetManifest":
        source_ids = _unique("source", [s.id for s in self.sources])
        text_ids = _unique("text", [t.id for t in self.texts])
        clip_ids = _unique("clip", [c.id for c in self.clips])
        clips = {c.id: c for c in self.clips}
        categories = {t.id: t.category for t in self.texts}
        for clip in self.clips:
            if clip.text_id not in text_ids:
                raise ValueError(f"clip {clip.id} names unknown text {clip.text_id}")
            if clip.source_id is not None and clip.source_id not in source_ids:
                raise ValueError(f"clip {clip.id} names unknown source {clip.source_id}")
            if clip.baseline_clip_id is not None:
                if clip.baseline_clip_id not in clip_ids:
                    raise ValueError(f"clip {clip.id} names unknown baseline")
                baseline = clips[clip.baseline_clip_id]
                if baseline.role is not ClipRole.GOLD or baseline.text_id != clip.text_id:
                    raise ValueError(
                        f"clip {clip.id} baseline must be a gold clip of the same text"
                    )
            is_extemporaneous = categories[clip.text_id] is Category.EXTEMPORANEOUS
            if is_extemporaneous and clip.role is not ClipRole.NORMATIVE_REFERENCE:
                raise ValueError(f"extemporaneous clip {clip.id} can only be a normative reference")
        return self


def _require(role: ClipRole, needed: bool, present: bool, thing: str) -> None:
    if needed != present:
        raise ValueError(f"{role.value} clips {'need' if needed else 'must not have'} {thing}")


def _unique(kind: str, ids: list[str]) -> set[str]:
    unique = set(ids)
    if len(unique) != len(ids):
        raise ValueError(f"duplicate {kind} ids")
    return unique
