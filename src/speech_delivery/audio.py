"""Mono 16 kHz audio, the one waveform type every package passes around."""

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from numpy.typing import NDArray

SAMPLE_RATE = 16_000


class AudioDecodeError(ValueError):
    """The file is not audio that ffmpeg can decode."""


@dataclass(frozen=True, slots=True)
class Audio:
    """Mono float32 samples in [-1, 1]. The sample rate is always `SAMPLE_RATE`."""

    samples: NDArray[np.float32]

    @property
    def duration_s(self) -> float:
        return len(self.samples) / SAMPLE_RATE


def from_samples(samples: NDArray[Any]) -> Audio:
    """Wrap samples, converting to contiguous float32 so equal audio hashes equal."""
    return Audio(np.ascontiguousarray(samples, dtype=np.float32))


def decode(path: Path) -> Audio:
    """Decode any ffmpeg-readable file to mono 16 kHz.

    ffmpeg's own mono downmix is not a mean and can clip correlated channels, so the file is
    decoded to stereo and the two channels are averaged here.
    """
    command = [
        "ffmpeg", "-v", "error", "-nostdin", "-i", str(path),
        "-vn", "-ac", "2", "-ar", str(SAMPLE_RATE), "-f", "f32le", "pipe:1",
    ]  # fmt: skip
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0 or not result.stdout:
        detail = result.stderr.decode(errors="replace").strip() or "no audio stream"
        raise AudioDecodeError(f"cannot decode {path.name}: {detail}")
    stereo = np.frombuffer(result.stdout, dtype="<f4").reshape(-1, 2)
    return from_samples(stereo.mean(axis=1))


def read_flac(path: Path) -> Audio:
    samples, rate = sf.read(path, dtype="float32", always_2d=False)
    array: NDArray[Any] = np.asarray(samples)
    if rate != SAMPLE_RATE or array.ndim != 1:
        raise AudioDecodeError(f"{path.name} must be mono {SAMPLE_RATE} Hz FLAC")
    return from_samples(array)


def write_flac(path: Path, audio: Audio) -> None:
    """Write 16-bit FLAC. The same samples always produce the same bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, audio.samples, SAMPLE_RATE, format="FLAC", subtype="PCM_16")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()
