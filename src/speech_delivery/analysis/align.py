"""MMS CTC alignment with bounded inference on CPU or an opt-in CUDA device."""

import logging
import os
from itertools import pairwise
from threading import Lock

import numpy as np
import torch
import torchaudio

from ..audio import SAMPLE_RATE, Audio
from ..contract import ErrorCode, Word, WordAlignment
from ..text import normalize, sentence_spans, tokens
from .protocol import AnalysisError

_MODEL_LOCK = Lock()
_cached_model: torch.nn.Module | None = None
# MMS's convolution has a 320-sample stride and a 400-sample receptive field.
_FRAME_SAMPLES = 320
_RECEPTIVE_SAMPLES = 400
_CORE_FRAMES = 1500
_CONTEXT_FRAMES = 100
# espeak calibration: true text 0.8131, unrelated text 0.1719 on the same clip.
_MIN_CONFIDENCE = 0.35
logger = logging.getLogger(__name__)


def runtime_info() -> dict[str, str | bool | None]:
    """Report configuration and the actual cached device without loading model weights."""
    actual = None
    if _cached_model is not None:
        actual = str(next(_cached_model.parameters()).device)
    return {
        "requested_alignment_device": os.environ.get("SPEECH_DEVICE", "cpu"),
        "loaded_alignment_device": actual,
        "cuda_available": torch.cuda.is_available(),
        "torch_version": str(torch.__version__),
    }


def _model() -> torch.nn.Module:
    global _cached_model
    if _cached_model is None:
        # One thread avoids reduction-order changes and oversubscription in API workers.
        torch.set_num_threads(1)
        torch.manual_seed(0)
        device = os.environ.get("SPEECH_DEVICE", "cpu")
        if device not in {"cpu", "cuda"}:
            raise ValueError("SPEECH_DEVICE must be cpu or cuda.")
        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA is unavailable. Install CUDA-enabled PyTorch or use CPU.")
        logger.info("ALIGNMENT MODEL | loading MMS weights | requested_device=%s", device)
        _cached_model = torchaudio.pipelines.MMS_FA.get_model(with_star=False).to(device).eval()
        logger.info(
            "ALIGNMENT MODEL | ready | loaded_device=%s", next(_cached_model.parameters()).device
        )
    return _cached_model


def _emission(audio: Audio, model: torch.nn.Module) -> torch.Tensor:
    """Keep 30 s cores with 2 s context, on one global convolution-frame clock.

    Context is discarded, not averaged. Starts are stride-aligned, so stitching cannot
    duplicate or lose frames or accumulate timing drift on ten-minute recordings.
    Only the small (frames, 28) emission survives each model invocation.
    """
    count = (len(audio.samples) - _RECEPTIVE_SAMPLES) // _FRAME_SAMPLES + 1
    if count <= 0:
        raise AnalysisError(ErrorCode.ALIGNMENT_FAILED, "Audio is too short to align speech.")
    pieces: list[torch.Tensor] = []
    device = next(model.parameters()).device
    for first in range(0, count, _CORE_FRAMES):
        last = min(first + _CORE_FRAMES, count)
        context_first = max(0, first - _CONTEXT_FRAMES)
        context_last = min(count, last + _CONTEXT_FRAMES)
        start = context_first * _FRAME_SAMPLES
        end = (context_last - 1) * _FRAME_SAMPLES + _RECEPTIVE_SAMPLES
        waveform = torch.from_numpy(audio.samples[start:end]).unsqueeze(0).to(device)
        emission, _ = model(waveform)
        pieces.append(emission[:, first - context_first : last - context_first].cpu().clone())
    return torch.cat(pieces, dim=1)


def align(audio: Audio, transcript: str) -> WordAlignment:
    """Align quoted transcript words; reject unsupported digits and unrelated speech."""
    written = tokens(transcript)
    if any(any(character.isdigit() for character in word) for word in transcript.split()):
        raise AnalysisError(
            ErrorCode.TRANSCRIPT_MISMATCH,
            "Digits are not supported by the speech aligner. Write numbers as spoken words.",
        )
    dictionary = torchaudio.pipelines.MMS_FA.get_dict(star=None)
    spellings = tuple("".join(c for c in normalize(word) if c in dictionary) for word in written)
    if not spellings or not all(spellings):
        raise AnalysisError(ErrorCode.TRANSCRIPT_MISMATCH, "Transcript has no alignable words.")
    target_ids = [dictionary[c] for word in spellings for c in word]
    targets = torch.tensor([target_ids], dtype=torch.int32)
    frames = (len(audio.samples) - _RECEPTIVE_SAMPLES) // _FRAME_SAMPLES + 1
    repeats = sum(a == b for a, b in pairwise(target_ids))
    if frames <= 0 or len(target_ids) + repeats > frames:
        raise AnalysisError(
            ErrorCode.ALIGNMENT_FAILED, "Audio is too short for the transcript's characters."
        )
    if not np.all(np.isfinite(audio.samples)):
        raise AnalysisError(ErrorCode.UNSUPPORTED_AUDIO, "Audio must contain finite samples.")
    with _MODEL_LOCK, torch.inference_mode():
        emission = _emission(audio, _model())
        try:
            path, log_scores = torchaudio.functional.forced_align(emission, targets, blank=0)
        except RuntimeError as error:
            raise AnalysisError(
                ErrorCode.ALIGNMENT_FAILED, f"CTC alignment failed: {error}"
            ) from error
        probabilities = log_scores[0].exp()
        spans = torchaudio.functional.merge_tokens(path[0], probabilities, blank=0)
        # Blank-heavy wrong paths can look confident. Judge only the character frames.
        confidence = float(probabilities[path[0] != 0].mean())
        if confidence < _MIN_CONFIDENCE:
            raise AnalysisError(
                ErrorCode.TRANSCRIPT_MISMATCH,
                f"Audio does not match the transcript (character confidence {confidence:.3f}, "
                f"minimum {_MIN_CONFIDENCE:.2f}). Check the text and recording.",
            )
        words: list[Word] = []
        offset = 0
        frame_s = _FRAME_SAMPLES / SAMPLE_RATE
        for text, spelling in zip(written, spellings, strict=True):
            word_spans = spans[offset : offset + len(spelling)]
            first, last = word_spans[0].start, word_spans[-1].end
            words.append(
                Word(
                    text=text,
                    start=first * frame_s,
                    end=last * frame_s,
                    confidence=float(probabilities[first:last].mean()),
                )
            )
            offset += len(spelling)
    return WordAlignment(words=tuple(words), sentences=sentence_spans(written))


def heard_characters(audio: Audio) -> list[tuple[str, float]]:
    """What the model hears, as (letter, seconds) pairs from a greedy CTC decode.

    The letters are noisy and carry no word boundaries. They are used to find which part of a
    known text a recording covers, never as a transcript.
    """
    labels = torchaudio.pipelines.MMS_FA.get_labels(star=None)
    frame_s = _FRAME_SAMPLES / SAMPLE_RATE
    with _MODEL_LOCK, torch.inference_mode():
        emission = _emission(audio, _model())
    best = emission[0].argmax(dim=-1).tolist()
    heard: list[tuple[str, float]] = []
    previous = 0
    for frame, label in enumerate(best):
        if label != 0 and label != previous:
            heard.append((labels[label], frame * frame_s))
        previous = label
    return heard
