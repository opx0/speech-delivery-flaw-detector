from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from speech_delivery.audio import (
    SAMPLE_RATE,
    AudioDecodeError,
    decode,
    from_samples,
    read_flac,
    sha256_file,
    write_flac,
)


def _tone(seconds: float, rate: int, channels: int = 1) -> np.ndarray:
    t = np.arange(int(seconds * rate)) / rate
    wave = 0.5 * np.sin(2 * np.pi * 220 * t)
    return np.stack([wave] * channels, axis=1) if channels > 1 else wave


def test_decode_resamples_a_44k_stereo_file_to_mono_16k(tmp_path: Path) -> None:
    source = tmp_path / "in.wav"
    sf.write(source, _tone(2.0, 44_100, channels=2), 44_100)

    audio = decode(source)

    assert audio.duration_s == pytest.approx(2.0, abs=0.01)
    assert audio.samples.dtype == np.float32
    assert audio.samples.ndim == 1
    assert float(np.max(np.abs(audio.samples))) == pytest.approx(0.5, abs=0.02)


def test_decode_rejects_a_file_that_is_not_audio(tmp_path: Path) -> None:
    source = tmp_path / "notes.txt"
    source.write_text("this is not audio")

    with pytest.raises(AudioDecodeError, match=r"notes\.txt"):
        decode(source)


def test_flac_round_trip_is_within_16_bit_quantisation(tmp_path: Path) -> None:
    original = from_samples(_tone(1.0, SAMPLE_RATE))
    path = tmp_path / "clip.flac"

    write_flac(path, original)
    restored = read_flac(path)

    assert len(restored.samples) == len(original.samples)
    assert float(np.max(np.abs(restored.samples - original.samples))) <= 1 / 32768


def test_writing_the_same_samples_twice_gives_identical_bytes(tmp_path: Path) -> None:
    audio = from_samples(_tone(0.5, SAMPLE_RATE))

    write_flac(tmp_path / "a.flac", audio)
    write_flac(tmp_path / "b.flac", audio)

    assert sha256_file(tmp_path / "a.flac") == sha256_file(tmp_path / "b.flac")


def test_read_flac_rejects_the_wrong_sample_rate(tmp_path: Path) -> None:
    path = tmp_path / "44k.flac"
    sf.write(path, _tone(0.5, 44_100), 44_100, format="FLAC")

    with pytest.raises(AudioDecodeError, match="16000"):
        read_flac(path)
