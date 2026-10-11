"""Acoustic features extracted from one recording."""

from pydantic import Field, model_validator

from .taxonomy import FeatureName
from .units import ContractModel, Decibels, FiniteFloat, Hertz, Seconds


class Interval(ContractModel):
    start: Seconds
    end: Seconds

    @model_validator(mode="after")
    def _non_empty(self) -> "Interval":
        if self.end <= self.start:
            raise ValueError("interval must have positive length")
        return self


class FeatureTrack(ContractModel):
    """One feature sampled every `hop_s` seconds. Sample i is centred at `i * hop_s`.

    `None` marks frames where the feature is undefined, such as pitch in unvoiced speech.
    """

    name: FeatureName
    hop_s: Seconds = Field(gt=0)
    values: tuple[FiniteFloat | None, ...]


class MatrixTrack(ContractModel):
    """A multi-coefficient feature such as MFCCs. `frames[i]` is the vector at `i * hop_s`."""

    hop_s: Seconds = Field(gt=0)
    frames: tuple[tuple[FiniteFloat, ...], ...]

    @model_validator(mode="after")
    def _rectangular(self) -> "MatrixTrack":
        widths = {len(frame) for frame in self.frames}
        if len(widths) > 1:
            raise ValueError("matrix frames must all have the same width")
        return self


class SpeakerNorm(ContractModel):
    """The references that turn raw Hz and dB into speaker-relative semitones and decibels."""

    median_f0_hz: Hertz
    energy_reference_db: Decibels


class RecordingFeatures(ContractModel):
    duration_s: Seconds = Field(gt=0)
    norm: SpeakerNorm
    tracks: tuple[FeatureTrack, ...]
    mfcc: MatrixTrack | None
    pauses: tuple[Interval, ...]

    @model_validator(mode="after")
    def _unique_tracks(self) -> "RecordingFeatures":
        names = [track.name for track in self.tracks]
        if len(set(names)) != len(names):
            raise ValueError("each feature may appear in at most one track")
        return self

    def track(self, name: FeatureName) -> FeatureTrack:
        for track in self.tracks:
            if track.name == name:
                return track
        raise KeyError(name)
