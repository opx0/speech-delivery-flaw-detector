"""Independent espeak fixture and numeric WAV demo; no aligner or downloads."""

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, cast

import numpy as np
import parselmouth
import soundfile as sf
from numpy.typing import NDArray

from speech_delivery.audio import SAMPLE_RATE, Audio, decode, from_samples
from speech_delivery.contract.alignment import Word, WordAlignment
from speech_delivery.contract.dataset import HesitationParams
from speech_delivery.contract.taxonomy import FlawKind
from speech_delivery.dataset.inject import make_control, make_flawed, make_speaker_shifted
from speech_delivery.dataset.levels import parameters
from speech_delivery.text import normalize, sentence_spans, tokens

PASSAGE = (
    "Every morning the village wakes beneath a bright and hopeful sky. "
    "Our voices carry stories over fields and through the quiet valley. "
    "We gather by the river where the gentle waters turn to silver. "
    "A patient teacher shows the children how to read the changing seasons. "
    "They travel past the mountains seeking courage wisdom wonder and adventure. "
    "The evening brings a golden light across the gardens of our neighbors. "
    "Remember all the kindness that has made this place a home for everyone. "
    "Tomorrow we will build a better world with open hearts and steady hands."
)


def synth_speech(transcript: str = PASSAGE) -> tuple[Audio, WordAlignment]:
    chunks: list[NDArray[np.float32]] = [np.zeros(1600, dtype=np.float32)]
    words: list[Word] = []
    cursor = 1600
    written = tokens(transcript)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "word.wav"
        for index, token in enumerate(written):
            # Vary pitch between words so pitch-flattening has observable phrase prosody.
            subprocess.run(
                [
                    "espeak-ng",
                    "-v",
                    "en-us",
                    "-s",
                    "190",
                    "-p",
                    str(35 + index % 7 * 5),
                    "-w",
                    str(path),
                    normalize(token),
                ],
                check=True,
                capture_output=True,
            )
            samples = decode(path).samples
            active = np.flatnonzero(np.abs(samples) > 0.002)
            if not len(active):
                raise ValueError(f"espeak rendered no speech for {token!r}")
            samples = samples[max(0, int(active[0]) - 80) : int(active[-1]) + 81]
            words.append(
                Word(
                    text=token,
                    start=cursor / SAMPLE_RATE,
                    end=(cursor + len(samples)) / SAMPLE_RATE,
                    confidence=1.0,
                )
            )
            chunks.append(samples)
            cursor += len(samples)
            gap = 7200 if token.endswith((".", "!", "?")) else 960
            chunks.append(np.zeros(gap, dtype=np.float32))
            cursor += gap
    return from_samples(np.concatenate(chunks)), WordAlignment(
        words=tuple(words), sentences=sentence_spans(written)
    )


def f0(samples: NDArray[np.float32]) -> NDArray[np.float64]:
    praat = cast(Any, parselmouth)
    pitch: Any = praat.Sound(samples, SAMPLE_RATE).to_pitch_ac(
        time_step=0.01, pitch_floor=60, pitch_ceiling=450
    )
    values: NDArray[np.float64] = np.asarray(pitch.selected_array["frequency"], dtype=np.float64)
    return values[values > 0]


def rms(samples: NDArray[np.float32]) -> float:
    return float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))


def demo(directory: Path) -> None:
    """Write level-three artifacts and report measurements, without claiming listening."""
    audio, alignment = synth_speech()
    control = make_control(audio, alignment)
    directory.mkdir(parents=True, exist_ok=True)
    sf.write(directory / "gold.wav", audio.samples, SAMPLE_RATE, subtype="FLOAT")
    sf.write(directory / "control.wav", control.audio.samples, SAMPLE_RATE, subtype="FLOAT")
    error = audio.samples.astype(np.float64) - control.audio.samples
    snr = 10 * np.log10(np.sum(audio.samples.astype(np.float64) ** 2) / np.sum(error**2))
    print(
        json.dumps(
            {
                "clip": "control",
                "duration_s": control.audio.duration_s,
                "snr_db": float(snr),
                "correlation": float(np.corrcoef(audio.samples, control.audio.samples)[0, 1]),
                "max_alignment_error_s": 0.0,
            }
        )
    )
    for kind in FlawKind:
        result = make_flawed(audio, alignment, (kind,), 3, 19)
        sf.write(
            directory / f"{kind.value}.wav", result.audio.samples, SAMPLE_RATE, subtype="FLOAT"
        )
        measured: list[float] = []
        sites: list[int] = []
        for flaw in result.flaws:
            start, end = alignment.time_range(flaw.words)
            old = control.audio.samples[round(start * SAMPLE_RATE) : round(end * SAMPLE_RATE)]
            new = result.audio.samples[
                round(flaw.start * SAMPLE_RATE) : round(flaw.end * SAMPLE_RATE)
            ]
            if kind in (FlawKind.RUSH, FlawKind.DRAG):
                measured.append((end - start) / (flaw.end - flaw.start))
            elif kind is FlawKind.MONOTONE:
                measured.append(
                    float(np.std(12 * np.log2(f0(new))) / np.std(12 * np.log2(f0(old))))
                )
            elif kind is FlawKind.HESITATION:
                assert isinstance(flaw.injection, HesitationParams)
                index = flaw.injection.silences[0].after_word
                sites.append(index)
                old_gap = alignment.words[index + 1].start - alignment.words[index].end
                measured.append(
                    result.alignment.words[index + 1].start
                    - result.alignment.words[index].end
                    - old_gap
                )
            elif kind is FlawKind.PAUSE_COLLAPSE:
                index = flaw.words.first
                sites.append(index)
                measured.append(
                    (result.alignment.words[index + 1].start - result.alignment.words[index].end)
                    / (alignment.words[index + 1].start - alignment.words[index].end)
                )
            else:
                measured.append(float(20 * np.log10(rms(old[-640:]) / rms(new[-640:]))))
        repeated = make_flawed(audio, alignment, (kind,), 3, 19)
        digest = hashlib.sha256(result.audio.samples.tobytes()).hexdigest()
        assert digest == hashlib.sha256(repeated.audio.samples.tobytes()).hexdigest()
        print(
            json.dumps(
                {
                    "clip": kind.value,
                    "level": 3,
                    "intended": parameters(kind, 3).model_dump(mode="json"),
                    "measured_per_region": measured,
                    "gap_after_words": sites,
                    "duration_s": result.audio.duration_s,
                    "duration_delta_s": result.audio.duration_s - audio.duration_s,
                    "regions": [f.words.model_dump() for f in result.flaws],
                    "sha256": digest,
                    "repeat_identical": True,
                }
            )
        )
    shifted = make_speaker_shifted(audio, alignment, 3.0, 1.1)
    sf.write(directory / "speaker_shifted.wav", shifted.audio.samples, SAMPLE_RATE, subtype="FLOAT")
    print(
        json.dumps(
            {
                "clip": "speaker_shifted",
                "intended_semitones": 3.0,
                "formant_ratio": 1.1,
                "measured_semitones": float(
                    12
                    * np.log2(np.median(f0(shifted.audio.samples)) / np.median(f0(audio.samples)))
                ),
                "duration_delta_s": shifted.audio.duration_s - audio.duration_s,
            }
        )
    )
    print("Nobody has listened to these clips. Measurements do not establish perceptual quality.")


if __name__ == "__main__":
    demo(Path("/tmp/inject-demo"))
