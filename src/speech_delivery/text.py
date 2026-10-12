"""Transcript tokenisation shared by alignment, the library and the dataset builder.

A token is one whitespace-separated word as written, punctuation included, so a flaw card can
quote the speech exactly. `normalize` gives the form used to compare words and to feed the
aligner. Keeping both here means every package splits a transcript the same way.
"""

import re
from difflib import SequenceMatcher

from .contract import WordSpan

_APOSTROPHES = str.maketrans({"\u2019": "'", "\u2018": "'", "`": "'"})
_DROP = re.compile(r"[^a-z0-9']")
_SENTENCE_END = re.compile(r"[.!?][\"')\]\u201d\u2019]*$")


def normalize(token: str) -> str:
    """Lowercase letters, digits and apostrophes only. A hyphenated word becomes one word."""
    return _DROP.sub("", token.lower().translate(_APOSTROPHES)).strip("'")


def tokens(transcript: str) -> tuple[str, ...]:
    """Words as written. Tokens with nothing speakable in them, such as a dash, are dropped."""
    return tuple(token for token in transcript.split() if normalize(token))


def sentence_spans(words: tuple[str, ...]) -> tuple[WordSpan, ...]:
    """Partition tokens into sentences, splitting after a token that ends in . ! or ?

    Abbreviations such as "Mr." end a sentence early. The library texts are chosen to avoid them.
    """
    if not words:
        return ()
    spans: list[WordSpan] = []
    first = 0
    for index, word in enumerate(words):
        if _SENTENCE_END.search(word):
            spans.append(WordSpan(first=first, last=index))
            first = index + 1
    if first < len(words):
        spans.append(WordSpan(first=first, last=len(words) - 1))
    return tuple(spans)


def similarity(a: str, b: str) -> float:
    """Share of words two transcripts have in common, in order, from 0 to 1."""
    left = [normalize(token) for token in tokens(a)]
    right = [normalize(token) for token in tokens(b)]
    if not left or not right:
        return 0.0
    return SequenceMatcher(a=left, b=right, autojunk=False).ratio()
