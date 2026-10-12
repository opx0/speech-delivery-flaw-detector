"""Immutable severity parameters, shared by injection and acoustic checks.

Fade occupies the last 60% at every level: only its final dB loss changes, so
severity comparisons do not conflate a longer envelope with a deeper one.
Hesitation's template site is replaced with the selected word index at injection.
"""

from types import MappingProxyType

from speech_delivery.contract.dataset import (
    DragParams,
    EnergyFadeParams,
    HesitationParams,
    InsertedSilence,
    MonotoneParams,
    PauseCollapseParams,
    RushParams,
)
from speech_delivery.contract.taxonomy import FlawKind

type Params = (
    RushParams
    | DragParams
    | MonotoneParams
    | HesitationParams
    | PauseCollapseParams
    | EnergyFadeParams
)

LEVELS: MappingProxyType[FlawKind, tuple[Params, ...]] = MappingProxyType(
    {
        FlawKind.RUSH: tuple(RushParams(rate_factor=x) for x in (1.15, 1.3, 1.5, 1.8)),
        FlawKind.DRAG: tuple(DragParams(rate_factor=x) for x in (0.87, 0.77, 0.67, 0.55)),
        FlawKind.MONOTONE: tuple(
            MonotoneParams(pitch_excursion_retained=x) for x in (0.7, 0.45, 0.25, 0.05)
        ),
        FlawKind.HESITATION: tuple(
            HesitationParams(silences=(InsertedSilence(after_word=0, duration_s=x),))
            for x in (0.25, 0.5, 0.9, 1.5)
        ),
        FlawKind.PAUSE_COLLAPSE: tuple(
            PauseCollapseParams(pause_retained=x) for x in (0.7, 0.45, 0.2, 0.0)
        ),
        FlawKind.ENERGY_FADE: tuple(
            EnergyFadeParams(drop_db=x, fade_fraction=0.6) for x in (3, 6, 10, 16)
        ),
    }
)


def parameters(kind: FlawKind, level: int) -> Params:
    if level not in (1, 2, 3, 4):
        raise ValueError("level must be 1, 2, 3 or 4")
    return LEVELS[kind][level - 1]
