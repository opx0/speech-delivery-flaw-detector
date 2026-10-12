"""Deterministic, synthetic example payloads for every contract root.

They let the dashboard, the API and the evaluator be built in parallel against realistic data
before the real pipeline exists. `make contract` writes them to `contract/fixtures/`.
"""

import hashlib
import math
from pathlib import Path
from typing import Literal

from pydantic import TypeAdapter

from .alignment import Word, WordAlignment, WordSpan
from .dataset import (
    AudioFile,
    Category,
    ClipLabel,
    ClipRole,
    DatasetManifest,
    FlawLabel,
    License,
    PipelineStamp,
    RightsEvidence,
    RushParams,
    Sex,
    SourceRecord,
    Split,
    TextRecord,
)
from .jobs import (
    DemoClip,
    ErrorCode,
    FailedEvent,
    JobEvent,
    LibraryEntry,
    LibraryListing,
    ProgressEvent,
    Stage,
)
from .report import (
    AxisScore,
    BandExpected,
    BandReference,
    BandSeries,
    BaselineExpected,
    BaselineReference,
    BaselineSeries,
    Deviation,
    Explanation,
    FlawRegion,
    ModelStamp,
    OverlaySeries,
    ParticipantInfo,
    Report,
    RunStamp,
    WarpAnchor,
)
from .rubric import RubricWeights
from .taxonomy import FEATURE_SPECS, Axis, FeatureName, FlawKind

TEXT_ID = "gettysburg-address"
TRANSCRIPT: str = (
    "Four score and seven years ago our fathers brought forth on this continent, a new nation, "
    "conceived in Liberty, and dedicated to the proposition that all men are created equal. "
    "Now we are engaged in a great civil war, testing whether that nation, or any nation so "
    "conceived and so dedicated, can long endure. We are met on a great battle-field of that war."
)
HOP_S = 0.05
WORD_SECONDS = 0.38
COMMA_PAUSE = 0.25
SENTENCE_PAUSE = 0.6
RUSH_WORDS = (30, 37)
HESITATION_AFTER_WORD = 14
HESITATION_SECONDS = 0.7
FADE_WORDS = (57, 63)

Basis = Literal["baseline", "band"]


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _tokens() -> list[str]:
    return TRANSCRIPT.split()


def _alignment(*, rushed: bool, hesitant: bool) -> WordAlignment:
    words: list[Word] = []
    clock = 0.0
    for index, token in enumerate(_tokens()):
        length = WORD_SECONDS
        if rushed and RUSH_WORDS[0] <= index <= RUSH_WORDS[1]:
            length = WORD_SECONDS / 1.8
        words.append(
            Word(text=token, start=round(clock, 3), end=round(clock + length, 3), confidence=0.95)
        )
        clock += length
        if token.endswith("."):
            clock += SENTENCE_PAUSE
        elif token.endswith(","):
            clock += COMMA_PAUSE
        if hesitant and index == HESITATION_AFTER_WORD:
            clock += HESITATION_SECONDS
    spans: list[WordSpan] = []
    first = 0
    for index, token in enumerate(_tokens()):
        if token.endswith("."):
            spans.append(WordSpan(first=first, last=index))
            first = index + 1
    return WordAlignment(words=tuple(words), sentences=tuple(spans))


BASELINE_WORDS = _alignment(rushed=False, hesitant=False)
PARTICIPANT_WORDS = _alignment(rushed=True, hesitant=True)


def _curve(feature: FeatureName, t: float, *, participant: bool) -> float:
    wiggle = {
        FeatureName.SPEECH_RATE: 2.6 + 0.4 * math.sin(t / 2.0),
        FeatureName.PITCH: 3.0 * math.sin(t * 1.3),
        FeatureName.PITCH_VARIATION: 2.5 + 0.8 * math.sin(t / 1.7),
        FeatureName.ENERGY: -12.0 + 3.0 * math.sin(t * 0.9),
        FeatureName.PAUSE: 0.12 + 0.1 * math.sin(t * 0.5) ** 2,
        FeatureName.CLARITY: 14.0 + 2.0 * math.sin(t / 3.0),
    }[feature]
    if not participant:
        return wiggle
    start, end = PARTICIPANT_WORDS.time_range(WordSpan(first=RUSH_WORDS[0], last=RUSH_WORDS[1]))
    if feature is FeatureName.SPEECH_RATE and start <= t <= end:
        return wiggle * 1.8
    fade_start, fade_end = PARTICIPANT_WORDS.time_range(
        WordSpan(first=FADE_WORDS[0], last=FADE_WORDS[1])
    )
    if feature is FeatureName.ENERGY and fade_start <= t <= fade_end:
        return wiggle - 9.0 * (t - fade_start) / (fade_end - fade_start)
    return wiggle


def _series(feature: FeatureName, basis: Basis) -> OverlaySeries:
    duration = PARTICIPANT_WORDS.words[-1].end
    times = [round(i * HOP_S, 3) for i in range(int(duration / HOP_S) + 1)]
    participant = tuple(round(_curve(feature, t, participant=True), 3) for t in times)
    reference = [round(_curve(feature, t, participant=False), 3) for t in times]
    if basis == "baseline":
        return OverlaySeries(
            feature=feature,
            hop_s=HOP_S,
            participant=participant,
            expected=BaselineSeries(values=tuple(reference)),
        )
    margin = 0.25 * abs(max(reference) - min(reference)) + 0.1
    return OverlaySeries(
        feature=feature,
        hop_s=HOP_S,
        participant=participant,
        expected=BandSeries(
            low=tuple(round(v - margin, 3) for v in reference),
            high=tuple(round(v + margin, 3) for v in reference),
        ),
    )


def _region(
    region_id: str,
    kind: FlawKind,
    words: tuple[int, int],
    observed: float,
    expected: float,
    basis: Basis,
    severity: float,
    detail: str,
) -> FlawRegion:
    span = WordSpan(first=words[0], last=words[1])
    start, end = PARTICIPANT_WORDS.time_range(span)
    feature = {
        FlawKind.RUSH: FeatureName.SPEECH_RATE,
        FlawKind.HESITATION: FeatureName.PAUSE,
        FlawKind.ENERGY_FADE: FeatureName.ENERGY,
    }[kind]
    gap = observed - expected
    if basis == "baseline":
        reference = BaselineExpected(value=expected)
    else:
        reference = BandExpected(low=expected - abs(gap) / 3, high=expected + abs(gap) / 3)
    return FlawRegion(
        id=region_id,
        kind=kind,
        axis={
            FlawKind.RUSH: Axis.CADENCE,
            FlawKind.HESITATION: Axis.PAUSES,
            FlawKind.ENERGY_FADE: Axis.VOLUME,
        }[kind],
        start=start,
        end=end,
        words=span,
        severity=severity,
        deviation=Deviation(
            feature=feature,
            unit=FEATURE_SPECS[feature].unit,
            observed=observed,
            expected=reference,
            delta=round(gap, 3),
            z_score=round(gap / max(abs(expected), 1.0) * 4, 3),
        ),
        explanation=Explanation(
            headline={
                FlawKind.RUSH: "Rushed pacing",
                FlawKind.HESITATION: "Hesitation mid-phrase",
                FlawKind.ENERGY_FADE: "Fading energy",
            }[kind],
            detail=detail,
            quoted_text=PARTICIPANT_WORDS.quote(span),
        ),
    )


def report(basis: Basis) -> Report:
    regions = (
        _region(
            "cadence-1",
            FlawKind.RUSH,
            RUSH_WORDS,
            4.68,
            2.6,
            basis,
            0.8,
            "Speech rate rose to 4.7 words/s, 80% above the expected 2.6 words/s.",
        ),
        _region(
            "pauses-1",
            FlawKind.HESITATION,
            (HESITATION_AFTER_WORD, HESITATION_AFTER_WORD + 1),
            0.7,
            0.12,
            basis,
            0.55,
            "A 0.7 s silence interrupted the phrase where the expected pause is 0.12 s.",
        ),
        _region(
            "volume-1",
            FlawKind.ENERGY_FADE,
            FADE_WORDS,
            -21.0,
            -12.0,
            basis,
            0.65,
            "Vocal energy fell 9 dB across the closing words of the final sentence.",
        ),
    )
    weights = RubricWeights()
    raw = {Axis.CADENCE: 52.0, Axis.TONE: 88.5, Axis.PAUSES: 71.0, Axis.VOLUME: 66.25}
    scores = tuple(AxisScore(axis=a, score=s, weight=weights.weight(a)) for a, s in raw.items())
    reference = (
        BaselineReference(
            clip_id="gettysburg-address.gold",
            text_id=TEXT_ID,
            warp=(
                WarpAnchor(participant_s=0.0, baseline_s=0.0),
                WarpAnchor(
                    participant_s=PARTICIPANT_WORDS.words[-1].end,
                    baseline_s=BASELINE_WORDS.words[-1].end,
                ),
            ),
        )
        if basis == "baseline"
        else BandReference(n_reference_clips=12, bands_version="fixture-1")
    )
    return Report(
        participant=ParticipantInfo(
            filename="my-attempt.wav",
            duration_s=PARTICIPANT_WORDS.words[-1].end,
            audio_sha256=_hash("participant"),
        ),
        reference=reference,
        words=PARTICIPANT_WORDS,
        weights=weights,
        axis_scores=scores,
        overall=sum(s.score * s.weight for s in scores),
        regions=regions,
        overlay=tuple(_series(feature, basis) for feature in FeatureName),
        run=RunStamp(
            package_version="0.1.0",
            config_hash=_hash("config"),
            seed=0,
            models=(ModelStamp(name="fixture-aligner", revision="0"),),
        ),
    )


def _audio(clip_id: str, alignment: WordAlignment) -> AudioFile:
    return AudioFile(
        path=f"audio/{clip_id}.flac",
        sha256=_hash(clip_id),
        duration_s=round(alignment.words[-1].end + 0.2, 3),
        sample_rate_hz=16000,
    )


def manifest() -> DatasetManifest:
    gold_id = f"{TEXT_ID}.gold"
    stamp = PipelineStamp(name="inject", version="0.1.0", seed=0, config_hash=_hash("inject"))
    last_word = len(BASELINE_WORDS.words) - 1
    rush = FlawLabel(
        kind=FlawKind.RUSH,
        level=3,
        words=WordSpan(first=RUSH_WORDS[0], last=RUSH_WORDS[1]),
        start=BASELINE_WORDS.words[RUSH_WORDS[0]].start,
        end=BASELINE_WORDS.words[RUSH_WORDS[1]].end,
        injection=RushParams(rate_factor=1.5),
    )
    human = FlawLabel(
        kind=FlawKind.MONOTONE,
        level=2,
        words=WordSpan(first=0, last=last_word // 2),
        start=BASELINE_WORDS.words[0].start,
        end=BASELINE_WORDS.words[last_word // 2].end,
        injection=None,
    )

    def clip(
        suffix: str,
        role: ClipRole,
        *,
        sex: Sex = Sex.FEMALE,
        split: Split = Split.CALIBRATION,
        flaws: tuple[FlawLabel, ...] = (),
        source: str | None = None,
        pipeline: bool = False,
    ) -> ClipLabel:
        clip_id = f"{TEXT_ID}.{suffix}"
        root = role in (ClipRole.GOLD, ClipRole.NORMATIVE_REFERENCE)
        return ClipLabel(
            id=clip_id,
            text_id=TEXT_ID,
            role=role,
            split=split,
            speaker_sex=sex,
            audio=_audio(clip_id, BASELINE_WORDS),
            alignment=BASELINE_WORDS,
            baseline_clip_id=None if root else gold_id,
            source_id=source,
            pipeline=stamp if pipeline else None,
            flaws=flaws,
        )

    def source(source_id: str, speaker: str, sex: Sex, file: str) -> SourceRecord:
        return SourceRecord(
            id=source_id,
            title="The Gettysburg Address",
            speaker_name=speaker,
            speaker_sex=sex,
            page_url="https://archive.org/details/gettysburgaddress_150anniv_1311_librivox",
            audio_url=f"https://archive.org/download/gettysburgaddress_150anniv_1311_librivox/{file}",
            excerpt_start=0.0,
            excerpt_end=119.0,
            rights=RightsEvidence(
                license=License.PUBLIC_DOMAIN_MARK,
                evidence_url="https://creativecommons.org/publicdomain/mark/1.0/",
                verified=True,
                notes="Item metadata on the source page.",
            ),
        )

    return DatasetManifest(
        dataset_version="fixture-1",
        sources=(
            source("librivox-amb", "Ann Boulais", Sex.FEMALE, "gettysburgaddress_lincoln_amb.mp3"),
            source("librivox-dj", "Drew Johnson", Sex.MALE, "gettysburgaddress_lincoln_dj.mp3"),
        ),
        texts=(
            TextRecord(
                id=TEXT_ID,
                title="The Gettysburg Address",
                category=Category.DECLAMATION,
                transcript=TRANSCRIPT,
                transcript_url="https://www.gutenberg.org/files/1065/1065-h/1065-h.htm",
            ),
        ),
        clips=(
            clip("gold", ClipRole.GOLD, source="librivox-amb"),
            clip("control", ClipRole.CONTROL, pipeline=True),
            clip("rush-l3", ClipRole.FLAWED, flaws=(rush,), pipeline=True),
            clip("shifted-male", ClipRole.SPEAKER_SHIFTED, sex=Sex.MALE, pipeline=True),
            clip("reader-dj", ClipRole.NATURAL_READER, sex=Sex.MALE, source="librivox-dj"),
            clip("human-mono", ClipRole.HUMAN_FLAWED, split=Split.TEST, flaws=(human,)),
        ),
    )


def job_events() -> list[JobEvent]:
    events: list[JobEvent] = [
        ProgressEvent(job_id="job-0001", stage=stage, fraction=1.0, message=f"{stage.value} done")
        for stage in Stage
    ]
    events.append(
        FailedEvent(
            job_id="job-0002",
            code=ErrorCode.TRANSCRIPT_MISMATCH,
            message="The audio does not match the transcript.",
        )
    )
    return events


def library_listing() -> LibraryListing:
    gold = manifest().clips[0]
    return LibraryListing(
        entries=(
            LibraryEntry(
                text_id=TEXT_ID,
                title="The Gettysburg Address",
                category=Category.DECLAMATION,
                transcript=TRANSCRIPT,
                baseline_clip_id=gold.id,
                baseline_audio_url=f"/api/audio/{gold.id}",
                duration_s=gold.audio.duration_s,
            ),
        ),
        demos=(
            DemoClip(
                clip_id=f"{TEXT_ID}.rush-l3",
                text_id=TEXT_ID,
                title="Rushed middle section",
                description="The same address with one stretch read 1.5 times too fast.",
                audio_url=f"/api/audio/{TEXT_ID}.rush-l3",
                flaw_kinds=(FlawKind.RUSH,),
                level=3,
            ),
        ),
    )


def render_all() -> dict[str, str]:
    """File name to JSON text, in the canonical form the repository commits."""
    return {
        "report_contrast.json": report("baseline").model_dump_json(indent=2) + "\n",
        "report_normative.json": report("band").model_dump_json(indent=2) + "\n",
        "dataset_manifest.json": manifest().model_dump_json(indent=2) + "\n",
        "job_events.json": TypeAdapter(list[JobEvent]).dump_json(job_events(), indent=2).decode()
        + "\n",
        "library.json": library_listing().model_dump_json(indent=2) + "\n",
    }


def write_all(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, text in render_all().items():
        (directory / name).write_text(text, encoding="utf-8")
