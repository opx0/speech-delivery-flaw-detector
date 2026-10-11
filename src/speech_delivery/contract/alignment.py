"""Word-level forced alignment of a transcript to audio."""

from pydantic import model_validator

from .units import ContractModel, Seconds, UnitInterval, WordIndex


class Word(ContractModel):
    text: str
    start: Seconds
    end: Seconds
    confidence: UnitInterval

    @model_validator(mode="after")
    def _ends_after_start(self) -> "Word":
        if self.end < self.start:
            raise ValueError(f"word {self.text!r} ends before it starts")
        return self


class WordSpan(ContractModel):
    """Inclusive range of word indices."""

    first: WordIndex
    last: WordIndex

    @model_validator(mode="after")
    def _ordered(self) -> "WordSpan":
        if self.last < self.first:
            raise ValueError("span last index precedes first index")
        return self


class WordAlignment(ContractModel):
    """Words in spoken order, plus the sentence partition used for pause and fade rules."""

    words: tuple[Word, ...]
    sentences: tuple[WordSpan, ...]

    @model_validator(mode="after")
    def _consistent(self) -> "WordAlignment":
        if not self.words:
            raise ValueError("alignment needs at least one word")
        for before, after in zip(self.words, self.words[1:], strict=False):
            if after.start < before.end:
                raise ValueError(f"words overlap at {after.text!r}")
        expected_first = 0
        for sentence in self.sentences:
            if sentence.first != expected_first:
                raise ValueError("sentences must partition the words contiguously")
            expected_first = sentence.last + 1
        if expected_first != len(self.words):
            raise ValueError("sentences must cover every word")
        return self

    def time_range(self, span: WordSpan) -> tuple[float, float]:
        """Start and end seconds covered by `span`."""
        return self.words[span.first].start, self.words[span.last].end

    def quote(self, span: WordSpan) -> str:
        return " ".join(word.text for word in self.words[span.first : span.last + 1])
