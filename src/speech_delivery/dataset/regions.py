"""Seeded word-boundary regions with no shared words, even across flaw kinds.

Clips below 30 words request two regions per kind, longer clips request two to
four. Greedy round-robin allocation returns fewer only when no disjoint candidate
remains. Sentences below three words cannot host a phrase flaw; fade needs four.
"""

from dataclasses import dataclass

import numpy as np

from speech_delivery.contract.alignment import WordAlignment, WordSpan
from speech_delivery.contract.taxonomy import FlawKind


@dataclass(frozen=True, slots=True)
class Region:
    kind: FlawKind
    words: WordSpan
    after_word: int | None = None


def _candidates(alignment: WordAlignment, kind: FlawKind) -> list[Region]:
    result: list[Region] = []
    if kind is FlawKind.PAUSE_COLLAPSE:
        for sentence in alignment.sentences[:-1]:
            index = sentence.last
            if alignment.words[index + 1].start - alignment.words[index].end >= 0.3:
                result.append(Region(kind, WordSpan(first=index, last=index + 1), index))
        return result
    for sentence in alignment.sentences:
        count = sentence.last - sentence.first + 1
        if kind is FlawKind.ENERGY_FADE:
            for size in range(4, min(6, count) + 1):
                result.append(
                    Region(kind, WordSpan(first=sentence.last - size + 1, last=sentence.last))
                )
            continue
        maximum = 6 if kind is FlawKind.HESITATION else 8
        for size in range(3, min(maximum, count) + 1):
            for first in range(sentence.first, sentence.last - size + 2):
                span = WordSpan(first=first, last=first + size - 1)
                if kind is FlawKind.HESITATION:
                    for index in range(span.first, span.last):
                        token = alignment.words[index].text.rstrip("\"')]}\u201d\u2019")
                        if (
                            not token.endswith(tuple(",.;:!?"))
                            and alignment.words[index + 1].start - alignment.words[index].end
                            >= 1 / 16000
                        ):
                            result.append(Region(kind, span, index))
                else:
                    result.append(Region(kind, span))
    return result


def select_regions(
    alignment: WordAlignment, kinds: tuple[FlawKind, ...], seed: int
) -> tuple[Region, ...]:
    if len(set(kinds)) != len(kinds):
        raise ValueError("kinds must not contain duplicates")
    rng = np.random.default_rng(seed)
    # Scarce sentence-boundary candidates get first refusal, independent of caller order.
    ordered = tuple(sorted(kinds, key=lambda k: (len(_candidates(alignment, k)), k.value)))
    pools: dict[FlawKind, list[Region]] = {}
    targets: dict[FlawKind, int] = {}
    for kind in ordered:
        candidates = _candidates(alignment, kind)
        pools[kind] = [candidates[int(i)] for i in rng.permutation(len(candidates))]
        targets[kind] = 2 if len(alignment.words) < 30 else int(rng.integers(2, 5))
    chosen: list[Region] = []
    counts = dict.fromkeys(ordered, 0)
    for _ in range(4):
        for kind in ordered:
            if counts[kind] >= targets[kind]:
                continue
            for candidate in pools[kind]:
                if all(
                    candidate.words.last < other.words.first
                    or candidate.words.first > other.words.last
                    for other in chosen
                ):
                    chosen.append(candidate)
                    counts[kind] += 1
                    break
    return tuple(sorted(chosen, key=lambda region: region.words.first))
