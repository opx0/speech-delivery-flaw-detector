"""Unit-carrying scalar types and the base model shared by every contract model.

Every time is seconds and every pitch is semitones relative to the speaker's own median,
so two recordings of different speakers can be compared without converting anything.
"""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

Seconds = Annotated[float, Field(ge=0, allow_inf_nan=False, description="Time in seconds.")]
Hertz = Annotated[float, Field(gt=0, allow_inf_nan=False, description="Frequency in hertz.")]
Decibels = Annotated[float, Field(allow_inf_nan=False, description="Level in decibels.")]
Semitones = Annotated[
    float,
    Field(allow_inf_nan=False, description="Pitch in semitones relative to the speaker median."),
]
UnitInterval = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Score = Annotated[
    float, Field(ge=0, le=100, allow_inf_nan=False, description="Score from 0 to 100.")
]
FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]
WordIndex = Annotated[int, Field(ge=0, description="Zero-based index into a word alignment.")]

Identifier = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z0-9][a-z0-9_.-]*$", min_length=1, max_length=96),
]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


def _require_relative_posix(path: str) -> str:
    if path.startswith("/") or "\\" in path or ".." in path.split("/"):
        raise ValueError("path must be relative, use forward slashes and stay inside the dataset")
    return path


RelativePosixPath = Annotated[
    str,
    StringConstraints(min_length=1),
    AfterValidator(_require_relative_posix),
    Field(description="Forward-slash path relative to the dataset root."),
]


class ContractModel(BaseModel):
    """Immutable, closed model. Unknown fields are errors so schema drift fails loudly."""

    model_config = ConfigDict(
        frozen=True, extra="forbid", json_schema_serialization_defaults_required=True
    )
