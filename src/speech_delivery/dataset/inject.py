"""Signal-level flaws and ground truth in the edited clip's sample clock."""

import math
from dataclasses import dataclass

import numpy as np

from speech_delivery.audio import SAMPLE_RATE, Audio
from speech_delivery.contract.alignment import Word, WordAlignment
from speech_delivery.contract.dataset import (
    DragParams,
    EnergyFadeParams,
    FlawLabel,
    HesitationParams,
    InsertedSilence,
    MonotoneParams,
    RushParams,
)
from speech_delivery.contract.taxonomy import FlawKind
from speech_delivery.dataset.dsp import (
    Edit,
    crossfade_edges,
    fade,
    neutral,
    peak_safe,
    psola,
    sample_index,
    silence_edit,
    speaker_shift,
    splice,
)
from speech_delivery.dataset.levels import Params, parameters
from speech_delivery.dataset.regions import select_regions


@dataclass(frozen=True, slots=True)
class Injected:
    audio: Audio
    alignment: WordAlignment
    flaws: tuple[FlawLabel, ...]


def _validate(audio: Audio, alignment: WordAlignment) -> None:
    if (
        audio.samples.ndim != 1
        or len(audio.samples) == 0
        or not np.isfinite(audio.samples).all()
        or np.max(np.abs(audio.samples)) > 1
    ):
        raise ValueError("audio must be nonempty finite mono samples in [-1, 1]")
    if alignment.words[-1].end > audio.duration_s:
        raise ValueError("alignment extends past audio")


def make_control(audio: Audio, alignment: WordAlignment) -> Injected:
    _validate(audio, alignment)
    return Injected(peak_safe(neutral(audio.samples)), alignment, ())


def make_speaker_shifted(
    audio: Audio, alignment: WordAlignment, semitones: float, formant_ratio: float
) -> Injected:
    _validate(audio, alignment)
    if not math.isfinite(semitones) or not math.isfinite(formant_ratio) or formant_ratio <= 0:
        raise ValueError("shift must be finite and formant_ratio must be positive")
    base = neutral(audio.samples)
    shifted = (
        base
        if semitones == 0 and formant_ratio == 1
        else speaker_shift(base, semitones, formant_ratio)
    )
    return Injected(peak_safe(crossfade_edges(base, shifted)), alignment, ())


def make_flawed(
    audio: Audio,
    alignment: WordAlignment,
    kinds: tuple[FlawKind, ...],
    level: int,
    seed: int,
) -> Injected:
    _validate(audio, alignment)
    if level not in (1, 2, 3, 4):
        raise ValueError("level must be 1, 2, 3 or 4")
    regions = select_regions(alignment, kinds, seed)
    base = neutral(audio.samples)
    edits: list[Edit] = []
    injections: list[Params] = []
    for region in regions:
        params = parameters(region.kind, level)
        start, end = alignment.time_range(region.words)
        first, last = sample_index(start), sample_index(end)
        original = base[first:last]
        if isinstance(params, (RushParams, DragParams)):
            changed = crossfade_edges(original, psola(original, rate=params.rate_factor))
        elif isinstance(params, MonotoneParams):
            changed = crossfade_edges(
                original, psola(original, retained=params.pitch_excursion_retained)
            )
        elif isinstance(params, EnergyFadeParams):
            changed = fade(original, params.drop_db, params.fade_fraction)
        else:
            if region.after_word is None:
                raise ValueError("a silence edit requires a gap site")
            index = region.after_word
            first = sample_index(alignment.words[index].end)
            last = sample_index(alignment.words[index + 1].start)
            original = base[first:last]
            if isinstance(params, HesitationParams):
                duration = params.silences[0].duration_s
                params = HesitationParams(
                    silences=(InsertedSilence(after_word=index, duration_s=duration),)
                )
                changed = silence_edit(original, round(duration * SAMPLE_RATE), insert=True)
            else:
                changed = silence_edit(
                    original, round(len(original) * params.pause_retained), insert=False
                )
        edits.append(Edit(first, last, changed))
        injections.append(params)
    samples, clock = splice(base, tuple(edits))
    mapped = WordAlignment(
        words=tuple(
            Word(
                text=word.text,
                start=clock(word.start),
                end=clock(word.end),
                confidence=word.confidence,
            )
            for word in alignment.words
        ),
        sentences=alignment.sentences,
    )
    flaws = tuple(
        FlawLabel(
            kind=region.kind,
            level=level,
            start=mapped.words[region.words.first].start,
            end=mapped.words[region.words.last].end,
            words=region.words,
            injection=params,
        )
        for region, params in zip(regions, injections, strict=True)
    )
    return Injected(peak_safe(samples), mapped, flaws)
