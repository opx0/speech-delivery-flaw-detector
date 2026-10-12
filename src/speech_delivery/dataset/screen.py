"""Repeatable, objective audio suitability measurements for source excerpts."""

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from speech_delivery.audio import SAMPLE_RATE, decode

_MIN_DURATION_S = 40.0
_MAX_DURATION_S = 150.0
_CLIP_THRESHOLD = 0.999
_NOISE_FLOOR_MAX_DBFS = -45.0
_SILENCE_DBFS = -50.0
_LONG_SILENCE_S = 2.0


@dataclass(frozen=True, slots=True)
class ScreenReport:
    duration_s: float
    sample_rate_hz: int
    integrated_lufs: float
    true_peak_dbfs: float
    clipped_fraction: float
    leading_silence_s: float
    trailing_silence_s: float
    noise_floor_dbfs: float
    long_silence_count: int
    passed: bool
    reasons: tuple[str, ...]


def _run(command: list[str]) -> str:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode:
        raise ValueError(result.stderr.strip() or "ffmpeg analysis failed")
    return result.stderr


def _loudness(path: Path, start: float, end: float | None) -> tuple[float, float]:
    command = ["ffmpeg", "-hide_banner", "-nostdin"]
    if start:
        command.extend(["-ss", str(start)])
    command.extend(["-i", str(path)])
    if end is not None:
        command.extend(["-t", str(end - start)])
    output = _run([*command, "-af", "loudnorm=print_format=json", "-f", "null", "-"])
    match = re.search(r"\{\s*\"input_i\".*?\}", output, re.DOTALL)
    if match is None:
        raise ValueError("ffmpeg loudnorm did not emit JSON")
    values = json.loads(match.group())
    return float(values["input_i"]), float(values["input_tp"])


def _silence_runs(samples: np.ndarray, threshold: float) -> tuple[float, float, int]:
    frame = max(1, SAMPLE_RATE // 10)
    padded = np.pad(samples, (0, (-len(samples)) % frame))
    rms = np.sqrt(np.mean(padded.reshape(-1, frame) ** 2, axis=1))
    quiet = rms <= threshold
    lead = int(np.argmax(~quiet)) if np.any(~quiet) else len(quiet)
    trail = int(np.argmax(~quiet[::-1])) if np.any(~quiet) else len(quiet)
    runs = 0
    active = False
    run_start = 0
    for index, is_quiet in enumerate(quiet):
        if is_quiet and not active:
            active, run_start = True, index
        elif not is_quiet and active:
            runs += int((index - run_start) * 0.1 >= _LONG_SILENCE_S)
            active = False
    if active:
        runs += int((len(quiet) - run_start) * 0.1 >= _LONG_SILENCE_S)
    return lead * 0.1, trail * 0.1, runs


def screen(
    path: Path, *, excerpt_start: float = 0.0, excerpt_end: float | None = None
) -> ScreenReport:
    """Measure an audio file or requested excerpt without making subjective quality claims."""
    audio = decode(path).samples
    first = round(excerpt_start * SAMPLE_RATE)
    last = round(excerpt_end * SAMPLE_RATE) if excerpt_end is not None else len(audio)
    samples = audio[first:last]
    if not len(samples):
        raise ValueError("excerpt contains no samples")
    duration = len(samples) / SAMPLE_RATE
    loudness, peak = _loudness(path, excerpt_start, excerpt_end)
    threshold = 10 ** (_SILENCE_DBFS / 20)
    leading, trailing, long_silences = _silence_runs(samples, threshold)
    frame = max(1, SAMPLE_RATE // 10)
    padded = np.pad(samples, (0, (-len(samples)) % frame))
    rms = np.sqrt(np.mean(padded.reshape(-1, frame) ** 2, axis=1))
    noise_floor = float(20 * np.log10(max(float(np.percentile(rms, 10)), 1e-12)))
    reasons: list[str] = []
    if not _MIN_DURATION_S <= duration <= _MAX_DURATION_S:
        reasons.append(f"duration outside {_MIN_DURATION_S:.0f}-{_MAX_DURATION_S:.0f} s")
    clipped = float(np.mean(np.abs(samples) >= _CLIP_THRESHOLD))
    if clipped > 0 or peak > -0.1:
        reasons.append("clipped or peak above -0.1 dBFS")
    if noise_floor > _NOISE_FLOOR_MAX_DBFS:
        reasons.append(f"noise floor above {_NOISE_FLOOR_MAX_DBFS:.0f} dBFS")
    if long_silences:
        reasons.append("contains long silence")
    return ScreenReport(
        duration,
        SAMPLE_RATE,
        loudness,
        peak,
        clipped,
        leading,
        trailing,
        noise_floor,
        long_silences,
        not reasons,
        tuple(reasons),
    )
