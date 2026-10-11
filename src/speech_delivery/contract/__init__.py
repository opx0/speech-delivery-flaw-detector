"""The data contract shared by dataset building, analysis, evaluation, the API and the web app.

Everything here is a closed, immutable pydantic model. `schema_export` turns the models into
one JSON Schema bundle and the TypeScript types the dashboard compiles against.
"""

from .alignment import Word, WordAlignment, WordSpan
from .dataset import (
    AudioFile,
    Category,
    ClipLabel,
    ClipRole,
    DatasetManifest,
    FlawLabel,
    License,
    PipelineStamp,
    RightsEvidence,
    Sex,
    SourceRecord,
    Split,
    TextRecord,
)
from .features import FeatureTrack, Interval, MatrixTrack, RecordingFeatures, SpeakerNorm
from .jobs import (
    AnalyzeOptions,
    DoneEvent,
    ErrorCode,
    FailedEvent,
    JobEvent,
    LibraryEntry,
    ProgressEvent,
    Stage,
)
from .report import (
    AxisScore,
    BandReference,
    BaselineReference,
    Deviation,
    Explanation,
    FlawRegion,
    OverlaySeries,
    Report,
    RunStamp,
)
from .rubric import RubricWeights
from .taxonomy import FEATURE_SPECS, FLAW_SPECS, Axis, Direction, FeatureName, FlawKind

__all__ = [
    "FEATURE_SPECS",
    "FLAW_SPECS",
    "AnalyzeOptions",
    "AudioFile",
    "Axis",
    "AxisScore",
    "BandReference",
    "BaselineReference",
    "Category",
    "ClipLabel",
    "ClipRole",
    "DatasetManifest",
    "Deviation",
    "Direction",
    "DoneEvent",
    "ErrorCode",
    "Explanation",
    "FailedEvent",
    "FeatureName",
    "FeatureTrack",
    "FlawKind",
    "FlawLabel",
    "FlawRegion",
    "Interval",
    "JobEvent",
    "LibraryEntry",
    "License",
    "MatrixTrack",
    "OverlaySeries",
    "PipelineStamp",
    "ProgressEvent",
    "RecordingFeatures",
    "Report",
    "RightsEvidence",
    "RubricWeights",
    "RunStamp",
    "Sex",
    "SourceRecord",
    "SpeakerNorm",
    "Split",
    "Stage",
    "TextRecord",
    "Word",
    "WordAlignment",
    "WordSpan",
]
