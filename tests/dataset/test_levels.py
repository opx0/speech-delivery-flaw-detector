from itertools import pairwise
from types import MappingProxyType

import pytest

from speech_delivery.contract.dataset import (
    DragParams,
    EnergyFadeParams,
    HesitationParams,
    MonotoneParams,
    PauseCollapseParams,
    RushParams,
)
from speech_delivery.contract.taxonomy import FlawKind
from speech_delivery.dataset.levels import LEVELS, Params, parameters


def severity(params: Params) -> float:
    if isinstance(params, RushParams):
        return params.rate_factor
    if isinstance(params, DragParams):
        return 1 / params.rate_factor
    if isinstance(params, MonotoneParams):
        return 1 - params.pitch_excursion_retained
    if isinstance(params, HesitationParams):
        return params.silences[0].duration_s
    if isinstance(params, PauseCollapseParams):
        return 1 - params.pause_retained
    return params.drop_db


def test_literal_table_and_frozen_models() -> None:
    assert isinstance(LEVELS, MappingProxyType)
    assert set(LEVELS) == set(FlawKind)
    assert [parameters(FlawKind.RUSH, n).model_dump()["rate_factor"] for n in range(1, 5)] == [
        1.15,
        1.3,
        1.5,
        1.8,
    ]
    assert parameters(FlawKind.ENERGY_FADE, 3) == EnergyFadeParams(drop_db=10, fade_fraction=0.6)
    for kind, entries in LEVELS.items():
        assert len(entries) == 4
        assert all(entry.kind == kind for entry in entries)
        measured = [severity(entry) for entry in entries]
        assert all(a < b for a, b in pairwise(measured))
        assert all(entry.model_config.get("frozen") for entry in entries)


@pytest.mark.parametrize("level", [-1, 0, 5])
def test_invalid_level(level: int) -> None:
    with pytest.raises(ValueError, match="level"):
        parameters(FlawKind.RUSH, level)
