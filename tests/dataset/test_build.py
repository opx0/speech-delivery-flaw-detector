"""Cutting a recording to the words it covers. Uses the real aligner model on synthetic speech."""

import numpy as np
from tests.analysis.synth import synth_speech

from speech_delivery.audio import SAMPLE_RATE, Audio, from_samples
from speech_delivery.dataset.build import locate
from speech_delivery.text import tokens

BODY = (
    "Ask what the river carries and the river will answer slowly. "
    "It carries the cold of the mountains and the patience of stone. "
    "It carries every promise the rain ever made to the thirsty fields. "
    "So walk beside it and listen before you speak."
)
INTRO = "This recording is read for the library by a volunteer."


def _join(*parts: Audio) -> Audio:
    gap = np.zeros(int(0.4 * SAMPLE_RATE), dtype=np.float32)
    pieces: list[np.ndarray] = []  # type: ignore[type-arg]
    for part in parts:
        pieces.extend([part.samples, gap])
    return from_samples(np.concatenate(pieces))


def test_an_announcement_before_and_after_the_text_is_cut_away() -> None:
    body, _ = synth_speech(BODY)
    intro, _ = synth_speech(INTRO)
    outro, _ = synth_speech("End of the reading, this recording is in the public domain.")

    cut = locate(_join(intro, body, outro), tokens(BODY))

    assert cut.first_word == 0
    assert cut.last_word == len(tokens(BODY)) - 1
    assert cut.audio.duration_s < body.duration_s + 1.5
    assert cut.audio.duration_s > body.duration_s - 0.5
    assert cut.start_s > intro.duration_s * 0.8


def test_a_recording_that_stops_halfway_keeps_only_the_words_it_reads() -> None:
    half = " ".join(BODY.split()[:24])
    audio, _ = synth_speech(half)

    cut = locate(audio, tokens(BODY))

    assert cut.first_word == 0
    assert 18 <= cut.last_word <= 26
