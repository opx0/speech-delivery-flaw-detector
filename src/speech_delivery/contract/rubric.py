"""The scoring rubric: four delivery axes with weights that sum to one."""

from pydantic import Field, model_validator

from .taxonomy import Axis
from .units import ContractModel, UnitInterval

WEIGHT_TOLERANCE = 1e-6


class RubricWeights(ContractModel):
    cadence: UnitInterval = Field(default=0.25)
    tone: UnitInterval = Field(default=0.25)
    pauses: UnitInterval = Field(default=0.25)
    volume: UnitInterval = Field(default=0.25)

    @model_validator(mode="after")
    def _sum_to_one(self) -> "RubricWeights":
        total = self.cadence + self.tone + self.pauses + self.volume
        if abs(total - 1.0) > WEIGHT_TOLERANCE:
            raise ValueError(f"axis weights must sum to 1, got {total}")
        return self

    def weight(self, axis: Axis) -> float:
        return getattr(self, axis.value)
