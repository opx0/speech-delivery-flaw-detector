"""Build the frozen dataset from the downloaded recordings.

For every text the build cuts the gold reading and the natural readers to the words the
recording really covers, aligns them, injects flaws into the gold reading, and writes the
manifest, the FLAC files and the calibration. Run it with
`python -m speech_delivery.dataset.build`. It is deterministic.
"""

import argparse
import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from ..analysis.align import align, heard_characters
from ..analysis.calibrate import build_calibration
from ..analysis.calibration import save_calibration
from ..analysis.features import extract_features
from ..analysis.recording import Recording
from ..audio import SAMPLE_RATE, Audio, decode, from_samples, read_flac, sha256_file, write_flac
from ..contract import (
    AudioFile,
    ClipLabel,
    ClipRole,
    DatasetManifest,
    FlawKind,
    PipelineStamp,
    Sex,
    SourceRecord,
    Split,
    TextRecord,
    WordAlignment,
)
from ..library import MANIFEST_NAME, Library
from ..text import normalize, tokens
from .inject import Injected, make_control, make_flawed, make_speaker_shifted
from .registry import SOURCES, TEXTS

DATASET_VERSION = "1"
PIPELINE_VERSION = "1"
LEVELS = (1, 2, 3, 4)
MIXES: tuple[tuple[str, tuple[FlawKind, ...], int], ...] = (
    ("mix-pace-fade", (FlawKind.RUSH, FlawKind.ENERGY_FADE), 3),
    ("mix-stall-flat", (FlawKind.HESITATION, FlawKind.MONOTONE), 3),
)
SHIFTS: tuple[tuple[str, float, float, Sex], ...] = (
    ("shifted-higher", 4.0, 1.12, Sex.FEMALE),
    ("shifted-lower", -4.0, 0.9, Sex.MALE),
)
FEMALE_F0_HZ = 165.0
MALE_F0_HZ = 150.0
MIN_BLOCK = 12
MAX_EXTENDED_SHARE = 0.25
EDGE_PAD_S = 0.3
MIN_WORDS = 10
AUDIO_DIR = "audio"
_LETTERS = re.compile(r"[^a-z]")


@dataclass(frozen=True, slots=True)
class Cut:
    """A recording trimmed to the words it covers."""

    audio: Audio
    start_s: float
    end_s: float
    first_word: int
    last_word: int


def _letters(word: str) -> str:
    return _LETTERS.sub("", normalize(word))


def locate(audio: Audio, words: Sequence[str]) -> Cut:
    """Find which of `words` the recording reads, and where. Intros and outros are cut off."""
    heard = heard_characters(audio)
    heard_text = "".join(letter for letter, _ in heard)
    spellings = [_letters(word) for word in words]
    offsets: list[int] = []
    total = 0
    for spelling in spellings:
        offsets.append(total)
        total += len(spelling)
    target = "".join(spellings)
    matcher = SequenceMatcher(a=heard_text, b=target, autojunk=False)
    blocks = [b for b in matcher.get_matching_blocks() if b.size >= MIN_BLOCK]
    if not blocks:
        raise ValueError("the recording does not contain any of the text")
    first_char, last_char = blocks[0].b, blocks[-1].b + blocks[-1].size
    heard_start = heard[blocks[0].a][1]
    heard_end = heard[min(blocks[-1].a + blocks[-1].size, len(heard)) - 1][1]
    seconds_per_letter = (heard_end - heard_start) / max(last_char - first_char, 1)
    first = next(i for i, off in enumerate(offsets) if off >= first_char - 2)
    last = max(i for i, off in enumerate(offsets) if off + len(spellings[i]) <= last_char + 2)
    start, end = heard_start, heard_end
    # The decode drops letters, so well-matched stretches stop short of the real ends. When the
    # recording clearly covers most of the text, take the whole text and place the ends from the
    # measured letter rate. A recording that really starts or stops midway keeps its own range.
    if first_char <= MAX_EXTENDED_SHARE * len(target):
        first, start = 0, max(0.0, heard_start - first_char * seconds_per_letter)
    if len(target) - last_char <= MAX_EXTENDED_SHARE * len(target):
        last = len(words) - 1
        end = heard_end + (len(target) - last_char) * seconds_per_letter
    if last - first + 1 < MIN_WORDS:
        raise ValueError("the recording covers too few words of the text")
    low = max(0, round((start - EDGE_PAD_S) * SAMPLE_RATE))
    high = min(len(audio.samples), round((end + EDGE_PAD_S + 0.4) * SAMPLE_RATE))
    return Cut(
        from_samples(audio.samples[low:high]), low / SAMPLE_RATE, high / SAMPLE_RATE, first, last
    )


def _seed(clip_id: str) -> int:
    return int(hashlib.sha256(clip_id.encode()).hexdigest()[:8], 16)


def _stamp(name: str, seed: int, config: dict[str, object]) -> PipelineStamp:
    digest = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    return PipelineStamp(name=name, version=PIPELINE_VERSION, seed=seed, config_hash=digest)


def _estimate_sex(recording: Recording) -> Sex:
    f0 = recording.features.norm.median_f0_hz
    if f0 >= FEMALE_F0_HZ:
        return Sex.FEMALE
    return Sex.MALE if f0 <= MALE_F0_HZ else Sex.UNSPECIFIED


def _audio_file(path: Path, root: Path, audio: Audio) -> AudioFile:
    return AudioFile(
        path=path.relative_to(root).as_posix(),
        sha256=sha256_file(path),
        duration_s=len(audio.samples) / SAMPLE_RATE,
        sample_rate_hz=SAMPLE_RATE,
    )


def _text_of(source: SourceRecord) -> TextRecord:
    for text in TEXTS:
        if source.id.startswith(f"{text.id}-"):
            return text
    raise KeyError(source.id)


def _sources_by_text() -> dict[str, list[SourceRecord]]:
    grouped: dict[str, list[SourceRecord]] = {}
    for source in SOURCES:
        grouped.setdefault(_text_of(source).id, []).append(source)
    return grouped


@dataclass(frozen=True, slots=True)
class Reading:
    source: SourceRecord
    audio: Audio
    alignment: WordAlignment
    cut: Cut


def _prepare(source: SourceRecord, words: Sequence[str], raw: Path, label: str) -> Reading:
    print(f"  {label}: {source.id}", flush=True)
    full = decode(raw / f"{source.id}.mp3")
    cut = locate(full, words)
    transcript = " ".join(words[cut.first_word : cut.last_word + 1])
    return Reading(source, cut.audio, align(cut.audio, transcript), cut)


def _derived_clip(
    out: Path,
    text_id: str,
    gold_id: str,
    suffix: str,
    role: ClipRole,
    injected: Injected,
    stamp: PipelineStamp,
    speaker: Sex,
) -> ClipLabel:
    clip_id = f"{text_id}.{suffix}"
    path = out / AUDIO_DIR / f"{clip_id}.flac"
    write_flac(path, injected.audio)
    audio = read_flac(path)
    return ClipLabel(
        id=clip_id,
        text_id=text_id,
        role=role,
        split=Split.TEST,
        speaker_sex=speaker,
        audio=_audio_file(path, out, audio),
        alignment=injected.alignment,
        baseline_clip_id=gold_id,
        source_id=None,
        pipeline=stamp,
        flaws=injected.flaws,
    )


def _derived_clips(
    out: Path,
    text_id: str,
    gold_id: str,
    audio: Audio,
    alignment: WordAlignment,
    sex: Sex,
) -> list[ClipLabel]:
    """The control, every flaw at every level, the compound mixes and the speaker-shifted copies."""

    def make(suffix: str, role: ClipRole, injected: Injected, stamp: PipelineStamp, who: Sex):
        return _derived_clip(out, text_id, gold_id, suffix, role, injected, stamp, who)

    clips = [
        make(
            "control",
            ClipRole.CONTROL,
            make_control(audio, alignment),
            _stamp("control", 0, {"kind": "control"}),
            sex,
        )
    ]
    for kind in FlawKind:
        for level in LEVELS:
            suffix = f"{kind.value}-l{level}"
            seed = _seed(f"{text_id}.{suffix}")
            clips.append(
                make(
                    suffix,
                    ClipRole.FLAWED,
                    make_flawed(audio, alignment, (kind,), level, seed),
                    _stamp("inject", seed, {"kinds": [kind.value], "level": level}),
                    sex,
                )
            )
    for suffix, kinds, level in MIXES:
        seed = _seed(f"{text_id}.{suffix}")
        clips.append(
            make(
                suffix,
                ClipRole.FLAWED,
                make_flawed(audio, alignment, kinds, level, seed),
                _stamp("inject", seed, {"kinds": [k.value for k in kinds], "level": level}),
                sex,
            )
        )
    for suffix, semitones, formant, shifted_sex in SHIFTS:
        clips.append(
            make(
                suffix,
                ClipRole.SPEAKER_SHIFTED,
                make_speaker_shifted(audio, alignment, semitones, formant),
                _stamp("shift", 0, {"semitones": semitones, "formant_ratio": formant}),
                shifted_sex,
            )
        )
    return clips


def build(raw: Path, out: Path) -> DatasetManifest:
    clips: list[ClipLabel] = []
    texts: list[TextRecord] = []
    sources: list[SourceRecord] = []
    references: dict[str, Recording] = {}

    for text_id, group in _sources_by_text().items():
        record = next(t for t in TEXTS if t.id == text_id)
        written = tokens(record.transcript)
        print(f"{text_id}", flush=True)
        gold_source, readers = group[0], group[1:]
        gold = _prepare(gold_source, written, raw, "gold")
        words = tokens(" ".join(written[gold.cut.first_word : gold.cut.last_word + 1]))
        clip_text = " ".join(words)
        texts.append(record.model_copy(update={"transcript": clip_text}))

        gold_id = f"{text_id}.gold"
        gold_path = out / AUDIO_DIR / f"{gold_id}.flac"
        write_flac(gold_path, gold.audio)
        gold_audio = read_flac(gold_path)
        gold_recording = Recording(gold.alignment, extract_features(gold_audio, gold.alignment))
        sex = _estimate_sex(gold_recording)
        sources.append(_with_excerpt(gold_source, gold.cut))
        clips.append(
            ClipLabel(
                id=gold_id,
                text_id=text_id,
                role=ClipRole.GOLD,
                split=Split.CALIBRATION,
                speaker_sex=sex,
                audio=_audio_file(gold_path, out, gold_audio),
                alignment=gold.alignment,
                baseline_clip_id=None,
                source_id=gold_source.id,
                pipeline=None,
                flaws=(),
            )
        )
        references[gold_id] = gold_recording

        for number, source in enumerate(readers):
            reading = _prepare(source, words, raw, "reader")
            clip_id = f"{text_id}.reader-{source.id.removeprefix(f'{text_id}-')}"
            path = out / AUDIO_DIR / f"{clip_id}.flac"
            write_flac(path, reading.audio)
            audio = read_flac(path)
            recording = Recording(reading.alignment, extract_features(audio, reading.alignment))
            split = Split.CALIBRATION if number == 0 else Split.TEST
            sources.append(_with_excerpt(source, reading.cut))
            clips.append(
                ClipLabel(
                    id=clip_id,
                    text_id=text_id,
                    role=ClipRole.NATURAL_READER,
                    split=split,
                    speaker_sex=_estimate_sex(recording),
                    audio=_audio_file(path, out, audio),
                    alignment=reading.alignment,
                    baseline_clip_id=gold_id,
                    source_id=source.id,
                    pipeline=None,
                    flaws=(),
                )
            )
            if split is Split.CALIBRATION:
                references[clip_id] = recording

        print("  injecting", flush=True)
        clips.extend(_derived_clips(out, text_id, gold_id, gold_audio, gold.alignment, sex))

    manifest = DatasetManifest(
        dataset_version=DATASET_VERSION,
        sources=tuple(sources),
        texts=tuple(texts),
        clips=tuple(clips),
    )
    (out / MANIFEST_NAME).write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    library = Library.load(out)
    calibration = build_calibration(library, references)
    save_calibration(calibration, out / "calibration.json")
    print(f"{len(clips)} clips, calibration {calibration.version[:12]}", flush=True)
    return manifest


def _with_excerpt(source: SourceRecord, cut: Cut) -> SourceRecord:
    return source.model_copy(update={"excerpt_start": cut.start_s, "excerpt_end": cut.end_s})


def recalibrate(out: Path) -> None:
    """Recompute calibration.json from the stored alignments. No aligner, takes seconds."""
    library = Library.load(out)
    recordings: dict[str, Recording] = {}
    for clip in library.clips(split=Split.CALIBRATION):
        if clip.role in (ClipRole.GOLD, ClipRole.NATURAL_READER):
            recordings[clip.id] = Recording(
                clip.alignment, extract_features(library.audio(clip.id), clip.alignment)
            )
    calibration = build_calibration(library, recordings)
    save_calibration(calibration, out / "calibration.json")
    print(f"calibration {calibration.version[:12]} from {len(recordings)} readings", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--out", type=Path, default=Path("data/dataset"))
    parser.add_argument("--calibrate-only", action="store_true")
    args = parser.parse_args()
    if args.calibrate_only:
        recalibrate(args.out)
    else:
        build(args.raw, args.out)


if __name__ == "__main__":
    main()
