from pathlib import Path

import numpy as np
import pytest

from speech_delivery.audio import SAMPLE_RATE, from_samples, sha256_file, write_flac
from speech_delivery.contract import ClipLabel, ClipRole, DatasetManifest, Split
from speech_delivery.contract import fixtures as fx
from speech_delivery.library import MANIFEST_NAME, DatasetIntegrityError, Library


def _write_dataset(root: Path) -> DatasetManifest:
    """The fixture manifest with a real, tiny FLAC behind every clip."""
    manifest = fx.manifest()
    clips: list[ClipLabel] = []
    for index, clip in enumerate(manifest.clips):
        seconds = clip.audio.duration_s
        t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
        write_flac(
            root / clip.audio.path, from_samples(0.3 * np.sin(2 * np.pi * (200 + index) * t))
        )
        audio = clip.audio.model_copy(
            update={
                "sha256": sha256_file(root / clip.audio.path),
                "duration_s": len(t) / SAMPLE_RATE,
            }
        )
        clips.append(clip.model_copy(update={"audio": audio}))
    written = manifest.model_copy(update={"clips": tuple(clips)})
    (root / MANIFEST_NAME).write_text(written.model_dump_json(), encoding="utf-8")
    return written


@pytest.fixture
def library(tmp_path: Path) -> Library:
    _write_dataset(tmp_path)
    return Library.load(tmp_path)


def test_clips_filter_by_role_split_and_text(library: Library) -> None:
    assert [c.id for c in library.clips(role=ClipRole.GOLD)] == ["gettysburg-address.gold"]
    assert [c.id for c in library.clips(split=Split.TEST)] == ["gettysburg-address.human-mono"]
    assert library.clips(text_id="no-such-text") == ()


def test_audio_is_returned_when_its_hash_matches(library: Library) -> None:
    audio = library.audio("gettysburg-address.gold")

    assert audio.duration_s == pytest.approx(
        library.clip("gettysburg-address.gold").audio.duration_s
    )


def test_audio_is_refused_when_the_file_was_changed_after_the_manifest(
    library: Library, tmp_path: Path
) -> None:
    path = tmp_path / library.clip("gettysburg-address.gold").audio.path
    write_flac(path, from_samples(np.zeros(SAMPLE_RATE, dtype=np.float32)))

    with pytest.raises(DatasetIntegrityError, match="manifest hash"):
        library.audio("gettysburg-address.gold")


def test_match_text_accepts_a_light_misreading_and_rejects_other_text(library: Library) -> None:
    transcript = fx.TRANSCRIPT.lower().replace("men are", "people are")

    matched = library.match_text(transcript)

    assert matched is not None
    assert matched.id == fx.TEXT_ID
    assert library.match_text("Ask not what your country can do for you.") is None


def test_listing_offers_the_baseline_a_clean_control_and_the_level_three_flaw(
    library: Library,
) -> None:
    listing = library.listing()

    assert [entry.baseline_audio_url for entry in listing.entries] == [
        "/api/audio/gettysburg-address.gold"
    ]
    assert [demo.clip_id for demo in listing.demos] == [
        "gettysburg-address.control",
        "gettysburg-address.rush-l3",
    ]
    assert listing.demos[0].flaw_kinds == ()
    assert listing.demos[1].title == "The Gettysburg Address: rushed pacing"
