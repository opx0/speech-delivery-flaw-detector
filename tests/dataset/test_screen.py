from pathlib import Path

import numpy as np
import soundfile as sf

from speech_delivery.dataset.screen import screen

RATE = 16_000


def _write(path: Path, samples: np.ndarray) -> Path:
    sf.write(path, samples.astype(np.float32), RATE, subtype="FLOAT")
    return path


def _clean() -> np.ndarray:
    t = np.arange(RATE * 45) / RATE
    gate = ((t % 1.0) < 0.8).astype(np.float32)
    return (0.1 * np.sin(2 * np.pi * 180 * t) * gate + 0.00001 * np.sin(2 * np.pi * 53 * t)).astype(
        np.float32
    )


def test_screen_passes_clean_synthetic_reading(tmp_path: Path) -> None:
    report = screen(_write(tmp_path / "clean.wav", _clean()))
    assert report.passed
    assert report.duration_s == 45.0
    assert report.clipped_fraction == 0.0
    assert report.noise_floor_dbfs < -45.0


def test_screen_rejects_clipped_and_noisy_audio(tmp_path: Path) -> None:
    clipped = np.full(RATE * 45, 1.0, dtype=np.float32)
    clipped_report = screen(_write(tmp_path / "clipped.wav", clipped))
    assert "clipped or peak above -0.1 dBFS" in clipped_report.reasons
    noise = np.full(RATE * 45, 0.1, dtype=np.float32)
    noisy_report = screen(_write(tmp_path / "noisy.wav", noise))
    assert "noise floor above -45 dBFS" in noisy_report.reasons


def test_screen_rejects_long_silence(tmp_path: Path) -> None:
    samples = _clean()
    samples[RATE * 10 : RATE * 14] = 0
    report = screen(_write(tmp_path / "silence.wav", samples))
    assert report.long_silence_count == 1
    assert "contains long silence" in report.reasons
