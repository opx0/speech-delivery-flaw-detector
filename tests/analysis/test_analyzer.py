"""The analyzer end to end with a fake signal stage, so no aligner is loaded."""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from tests.analysis.synth import synth_speech

from speech_delivery.analysis.analyzer import build_analyzer
from speech_delivery.analysis.calibration import default_calibration
from speech_delivery.analysis.features import extract_features
from speech_delivery.analysis.protocol import AnalysisError
from speech_delivery.analysis.recording import Recording
from speech_delivery.audio import SAMPLE_RATE, Audio, sha256_file, write_flac
from speech_delivery.contract import (
    AnalyzeOptions,
    Category,
    ClipLabel,
    ClipRole,
    DatasetManifest,
    ErrorCode,
    RubricWeights,
    Stage,
    TextRecord,
    WordAlignment,
)
from speech_delivery.contract import fixtures as fx
from speech_delivery.contract.dataset import AudioFile, Sex, SourceRecord, Split
from speech_delivery.library import MANIFEST_NAME, Library

PASSAGE = (
    "We gather here today to remember what came before us. "
    "The people who built this place worked through long winters and short harvests. "
    "Their patience gave us the ground we now stand on."
)


@pytest.fixture(scope="module")
def spoken() -> tuple[Audio, WordAlignment]:
    return synth_speech(PASSAGE, pauses={9: 0.6, 21: 0.6})


@pytest.fixture
def library(tmp_path: Path, spoken: tuple[Audio, WordAlignment]) -> Library:
    audio, alignment = spoken
    template = fx.manifest()
    source: SourceRecord = template.sources[0]
    write_flac(tmp_path / "audio/passage.gold.flac", audio)
    clip = ClipLabel(
        id="passage.gold",
        text_id="passage",
        role=ClipRole.GOLD,
        split=Split.CALIBRATION,
        speaker_sex=Sex.UNSPECIFIED,
        audio=AudioFile(
            path="audio/passage.gold.flac",
            sha256=sha256_file(tmp_path / "audio/passage.gold.flac"),
            duration_s=audio.duration_s,
            sample_rate_hz=SAMPLE_RATE,
        ),
        alignment=alignment,
        baseline_clip_id=None,
        source_id=source.id,
        pipeline=None,
        flaws=(),
    )
    manifest = DatasetManifest(
        dataset_version="test",
        sources=(source,),
        texts=(
            TextRecord(
                id="passage",
                title="A Passage",
                category=Category.DECLAMATION,
                transcript=PASSAGE,
                transcript_url="https://example.org/passage",
            ),
        ),
        clips=(clip,),
    )
    (tmp_path / MANIFEST_NAME).write_text(manifest.model_dump_json(), encoding="utf-8")
    return Library.load(tmp_path)


def _fake_signal(spoken: tuple[Audio, WordAlignment]):  # type: ignore[no-untyped-def]
    """Stands in for alignment: every audio is treated as the synthetic reading."""
    audio, alignment = spoken

    def signal(_audio: Audio, _transcript: str) -> Recording:
        return Recording(alignment=alignment, features=extract_features(audio, alignment))

    return signal


def _upload(tmp_path: Path, spoken: tuple[Audio, WordAlignment], name: str = "me.wav") -> Path:
    path = tmp_path / name
    sf.write(path, spoken[0].samples, SAMPLE_RATE)
    return path


class Progress:
    def __init__(self) -> None:
        self.events: list[tuple[Stage, float]] = []

    def __call__(self, stage: Stage, fraction: float, message: str) -> None:
        assert message
        self.events.append((stage, fraction))


def test_a_matching_transcript_is_compared_with_the_gold_reading(
    library: Library, spoken: tuple[Audio, WordAlignment], tmp_path: Path
) -> None:
    analyzer = build_analyzer(library, default_calibration(), signal=_fake_signal(spoken))
    progress = Progress()

    report = analyzer.analyze(
        _upload(tmp_path, spoken), AnalyzeOptions(transcript=PASSAGE.lower()), progress
    )

    assert report.reference.basis == "baseline"
    assert report.reference.clip_id == "passage.gold"  # type: ignore[union-attr]
    assert report.overall == pytest.approx(100.0, abs=0.5)
    assert report.participant.filename == "me.wav"
    assert progress.events[0][0] is Stage.DECODE
    assert {stage for stage, _ in progress.events} == set(Stage)
    stages = [stage for stage, _ in progress.events]
    assert stages == sorted(stages, key=list(Stage).index)


def test_an_unknown_transcript_is_measured_against_bands(
    library: Library, spoken: tuple[Audio, WordAlignment], tmp_path: Path
) -> None:
    analyzer = build_analyzer(library, default_calibration(), signal=_fake_signal(spoken))

    report = analyzer.analyze(
        _upload(tmp_path, spoken),
        AnalyzeOptions(transcript="Ask not what your country can do for you."),
        Progress(),
    )

    assert report.reference.basis == "band"


def test_editing_the_weights_changes_the_overall_but_not_the_regions(
    library: Library, spoken: tuple[Audio, WordAlignment], tmp_path: Path
) -> None:
    analyzer = build_analyzer(library, default_calibration(), signal=_fake_signal(spoken))
    upload = _upload(tmp_path, spoken)
    equal = analyzer.analyze(upload, AnalyzeOptions(transcript=PASSAGE), Progress())
    skewed = analyzer.analyze(
        upload,
        AnalyzeOptions(
            transcript=PASSAGE,
            weights=RubricWeights(cadence=0.7, tone=0.1, pauses=0.1, volume=0.1),
        ),
        Progress(),
    )

    assert skewed.regions == equal.regions
    assert skewed.weights.cadence == 0.7


def test_the_same_upload_gives_the_same_report_bytes(
    library: Library, spoken: tuple[Audio, WordAlignment], tmp_path: Path
) -> None:
    analyzer = build_analyzer(library, default_calibration(), signal=_fake_signal(spoken))
    upload = _upload(tmp_path, spoken)
    options = AnalyzeOptions(transcript=PASSAGE)

    first = analyzer.analyze(upload, options, Progress())
    second = analyzer.analyze(upload, options, Progress())

    assert first.model_dump_json() == second.model_dump_json()


def test_errors_carry_the_code_the_participant_needs(
    library: Library, spoken: tuple[Audio, WordAlignment], tmp_path: Path
) -> None:
    analyzer = build_analyzer(library, default_calibration(), signal=_fake_signal(spoken))
    garbage = tmp_path / "notes.txt"
    garbage.write_text("not audio")

    with pytest.raises(AnalysisError) as unreadable:
        analyzer.analyze(garbage, AnalyzeOptions(transcript=PASSAGE), Progress())
    with pytest.raises(AnalysisError) as mismatch:
        analyzer.analyze(
            _upload(tmp_path, spoken),
            AnalyzeOptions(transcript="Something else entirely.", library_text_id="passage"),
            Progress(),
        )
    with pytest.raises(AnalysisError) as missing:
        analyzer.analyze(
            _upload(tmp_path, spoken),
            AnalyzeOptions(transcript=PASSAGE, library_text_id="no-such-text"),
            Progress(),
        )

    assert unreadable.value.code is ErrorCode.UNSUPPORTED_AUDIO
    assert mismatch.value.code is ErrorCode.TRANSCRIPT_MISMATCH
    assert missing.value.code is ErrorCode.TRANSCRIPT_MISMATCH


def test_a_recording_over_the_length_limit_is_refused(
    library: Library, spoken: tuple[Audio, WordAlignment], tmp_path: Path
) -> None:
    analyzer = build_analyzer(library, default_calibration(), signal=_fake_signal(spoken))
    long_path = tmp_path / "long.wav"
    sf.write(long_path, np.zeros(SAMPLE_RATE * 601, dtype=np.float32), SAMPLE_RATE)

    with pytest.raises(AnalysisError) as error:
        analyzer.analyze(long_path, AnalyzeOptions(transcript=PASSAGE), Progress())

    assert error.value.code is ErrorCode.TOO_LONG
