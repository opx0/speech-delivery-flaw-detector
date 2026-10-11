"""The HTTP boundary: what the dashboard sends and the events the job stream returns."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from .dataset import Category
from .report import Report
from .rubric import RubricWeights
from .units import ContractModel, Identifier, Seconds, UnitInterval

MAX_UPLOAD_SECONDS = 600
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


class Stage(StrEnum):
    DECODE = "decode"
    ALIGN = "align"
    EXTRACT = "extract"
    COMPARE = "compare"
    EXPLAIN = "explain"


class ErrorCode(StrEnum):
    UNSUPPORTED_AUDIO = "unsupported_audio"
    TOO_LONG = "too_long"
    TOO_LARGE = "too_large"
    TRANSCRIPT_MISMATCH = "transcript_mismatch"
    ALIGNMENT_FAILED = "alignment_failed"
    INTERNAL = "internal"


class AnalyzeOptions(ContractModel):
    """JSON sent beside the audio file. A transcript matching a library text selects the
    contrast mode, anything else selects the normative mode."""

    transcript: str = Field(min_length=1)
    library_text_id: Identifier | None = None
    weights: RubricWeights | None = None


class LibraryEntry(ContractModel):
    """A speech the participant can read and be compared against."""

    text_id: Identifier
    title: str
    category: Category
    transcript: str
    baseline_clip_id: Identifier
    baseline_audio_url: str
    duration_s: Seconds = Field(gt=0)


class ProgressEvent(ContractModel):
    type: Literal["progress"] = "progress"
    job_id: Identifier
    stage: Stage
    fraction: UnitInterval
    message: str


class DoneEvent(ContractModel):
    type: Literal["done"] = "done"
    job_id: Identifier
    report: Report


class FailedEvent(ContractModel):
    type: Literal["failed"] = "failed"
    job_id: Identifier
    code: ErrorCode
    message: str


JobEvent = Annotated[ProgressEvent | DoneEvent | FailedEvent, Field(discriminator="type")]
