import json
from pathlib import Path

import pytest

from speech_delivery.contract.dataset import License, RightsEvidence, Sex, SourceRecord
from speech_delivery.dataset.acquire import clean_transcript, fetch
from speech_delivery.dataset.registry import TEXTS


def _source() -> SourceRecord:
    return SourceRecord(
        id="fixture",
        title="Fixture",
        speaker_name="Reader",
        speaker_sex=Sex.UNSPECIFIED,
        page_url="https://example.test/page",
        audio_url="https://example.test/audio.mp3",
        excerpt_start=0.0,
        excerpt_end=60.0,
        rights=RightsEvidence(
            license=License.CC0,
            evidence_url="https://example.test/rights",
            verified=True,
            notes="CC0",
        ),
    )


def test_fetch_reuses_file_matching_recorded_checksum(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    audio = raw / "fixture.mp3"
    audio.write_bytes(b"stable fixture")
    import hashlib

    digest = hashlib.sha256(b"stable fixture").hexdigest()
    (raw / "checksums.json").write_text(json.dumps({"fixture": digest}))
    assert fetch(_source(), raw) == audio


def test_fetch_refuses_changed_existing_file(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "fixture.mp3").write_bytes(b"changed")
    (raw / "checksums.json").write_text(json.dumps({"fixture": "0" * 64}))
    with pytest.raises(ValueError, match="differs"):
        fetch(_source(), raw)


def test_clean_transcript_matches_committed_small_sample() -> None:
    expected = TEXTS[0].transcript
    sample = f"<p>{expected}</p><sup>[1]</sup>"
    assert clean_transcript(sample) == expected
