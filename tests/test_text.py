import pytest

from speech_delivery.contract import WordSpan
from speech_delivery.text import normalize, sentence_spans, similarity, tokens


def test_tokens_keep_punctuation_and_drop_unspeakable_marks() -> None:
    assert tokens("Four score, and  seven \u2014 years ago.") == (
        "Four",
        "score,",
        "and",
        "seven",
        "years",
        "ago.",
    )


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("Liberty,", "liberty"),
        ("battle-field", "battlefield"),
        ("don\u2019t", "don't"),
        ("'quoted'", "quoted"),
        ("1776.", "1776"),
    ],
)
def test_normalize(token: str, expected: str) -> None:
    assert normalize(token) == expected


def test_sentence_spans_split_after_terminal_punctuation_and_keep_the_tail() -> None:
    words = tokens('He said "stop!" Then he left. And so on')

    assert sentence_spans(words) == (
        WordSpan(first=0, last=2),
        WordSpan(first=3, last=5),
        WordSpan(first=6, last=8),
    )


def test_similarity_ignores_case_and_punctuation_but_not_missing_words() -> None:
    original = "Four score and seven years ago, our fathers brought forth."

    assert similarity(original, "four score AND seven years ago our fathers brought forth") == 1.0
    assert similarity(original, "Four score and seven years ago") == pytest.approx(2 * 6 / (10 + 6))
    assert similarity(original, "") == 0.0
