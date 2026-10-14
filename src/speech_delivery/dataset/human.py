"""Import genuine, consented held-out takes into a new dataset, using CUDA alignment.

The input is a JSON array of takes. Each take supplies clip_id, speaker_id, speaker_sex,
text_id, take (clean/rush/monotone/hesitation), audio (relative to the JSON file), license,
permission_to_publish, and flaws (FlawLabel objects with injection=null).
"""

import argparse
import json
import os
import shutil
from enum import StrEnum
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

import torch
from pydantic import Field, TypeAdapter, model_validator

from ..analysis.align import align
from ..audio import SAMPLE_RATE, decode, sha256_file, write_flac
from ..contract.dataset import (
    AudioFile,
    ClipLabel,
    ClipRole,
    DatasetManifest,
    FlawLabel,
    Sex,
    Split,
)
from ..contract.jobs import MAX_UPLOAD_BYTES, MAX_UPLOAD_SECONDS
from ..contract.taxonomy import FlawKind
from ..contract.units import ContractModel, Identifier, RelativePosixPath
from ..library import MANIFEST_NAME, Library


class TakeKind(StrEnum):
    CLEAN = "clean"
    RUSH = "rush"
    MONOTONE = "monotone"
    HESITATION = "hesitation"


class HumanTake(ContractModel):
    clip_id: Identifier
    speaker_id: Identifier
    speaker_sex: Sex = Sex.UNSPECIFIED
    text_id: Identifier
    take: TakeKind
    audio: RelativePosixPath
    license: Literal["cc-by-4.0", "original-recording"]
    permission_to_publish: bool
    flaws: tuple[FlawLabel, ...] = Field(default=())

    @model_validator(mode="after")
    def _human_only(self) -> "HumanTake":
        if not self.permission_to_publish:
            raise ValueError("explicit permission to publish is required")
        if (self.take is TakeKind.CLEAN) != (not self.flaws):
            raise ValueError("clean takes have no flaws; flawed takes require human labels")
        for flaw in self.flaws:
            if flaw.injection is not None:
                raise ValueError("human labels cannot contain synthetic injection parameters")
            if flaw.kind is not FlawKind(self.take.value):
                raise ValueError("flaw labels must match the declared take")
        return self


def validate_recording_plan(takes: list[HumanTake], *, allow_partial: bool = False) -> None:
    keys = {(take.speaker_id, take.text_id, take.take) for take in takes}
    if not takes or len(keys) != len(takes) or len({take.clip_id for take in takes}) != len(takes):
        raise ValueError(
            "takes must be nonempty with unique IDs and speaker/text/take combinations"
        )
    for speaker in {take.speaker_id for take in takes}:
        if len({take.speaker_sex for take in takes if take.speaker_id == speaker}) != 1:
            raise ValueError(f"inconsistent speaker metadata for {speaker}")
    if allow_partial:
        return
    speakers = {take.speaker_id for take in takes}
    texts = {take.text_id for take in takes}
    expected = {
        (speaker, text, kind) for speaker in speakers for text in texts for kind in TakeKind
    }
    if len(speakers) != 2 or len(texts) != 2 or keys != expected:
        raise ValueError(
            "the complete held-out set needs two speakers, two texts, and four takes each"
        )


def import_takes(
    dataset: Path, labels: Path, output: Path, version: str, *, allow_partial: bool = False
) -> None:
    takes = TypeAdapter(list[HumanTake]).validate_json(labels.read_text(encoding="utf-8"))
    validate_recording_plan(takes, allow_partial=allow_partial)
    library = Library.load(dataset)
    if output.exists() or output.resolve() == dataset.resolve():
        raise ValueError("output must be a new directory; published datasets are never overwritten")
    if output.resolve().is_relative_to(dataset.resolve()):
        raise ValueError("output cannot be nested inside the base dataset")
    if not version.strip() or version == library.manifest.dataset_version:
        raise ValueError("provide a distinct, nonempty dataset version")
    if any(clip.role in {ClipRole.HUMAN_CLEAN, ClipRole.HUMAN_FLAWED} for clip in library.clips()):
        raise ValueError("import from a base dataset without human-held-out clips")
    existing = {clip.id for clip in library.clips()}
    files: dict[str, Path] = {}
    for take in takes:
        library.text(take.text_id)
        if take.clip_id in existing:
            raise ValueError(f"clip ID already exists: {take.clip_id}")
        audio = (labels.parent / take.audio).resolve()
        if not audio.is_relative_to(labels.parent.resolve()) or not audio.is_file():
            raise ValueError(f"audio must exist within the labels directory: {take.audio}")
        if audio.stat().st_size > MAX_UPLOAD_BYTES:
            raise ValueError(f"recording exceeds the upload limit: {take.clip_id}")
        files[take.clip_id] = audio
    if not (dataset / "audio").is_dir():
        raise ValueError("extract the base dataset audio before importing")
    if os.environ.get("SPEECH_DEVICE") != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("import requires SPEECH_DEVICE=cuda and CUDA-enabled PyTorch")

    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="human-import-", dir=output.parent) as temporary:
        stage = Path(temporary) / "dataset"
        shutil.copytree(dataset, stage)
        clips = list(library.manifest.clips)
        for take in takes:
            audio = decode(files[take.clip_id])
            if audio.duration_s > MAX_UPLOAD_SECONDS:
                raise ValueError(f"recording exceeds ten minutes: {take.clip_id}")
            transcript = library.text(take.text_id).transcript
            alignment = align(audio, transcript)
            path = stage / "audio" / f"{take.clip_id}.flac"
            if path.exists():
                raise ValueError(f"audio output already exists: {take.clip_id}")
            write_flac(path, audio)
            clips.append(
                ClipLabel(
                    id=take.clip_id,
                    text_id=take.text_id,
                    role=ClipRole.HUMAN_FLAWED if take.flaws else ClipRole.HUMAN_CLEAN,
                    split=Split.TEST,
                    speaker_sex=take.speaker_sex,
                    audio=AudioFile(
                        path=path.relative_to(stage).as_posix(),
                        sha256=sha256_file(path),
                        duration_s=audio.duration_s,
                        sample_rate_hz=SAMPLE_RATE,
                    ),
                    alignment=alignment,
                    baseline_clip_id=library.gold_for(take.text_id).id,
                    source_id=None,
                    pipeline=None,
                    flaws=take.flaws,
                )
            )
        manifest = DatasetManifest(
            dataset_version=version,
            sources=library.manifest.sources,
            texts=library.manifest.texts,
            clips=tuple(clips),
        )
        (stage / MANIFEST_NAME).write_text(manifest.model_dump_json(indent=2) + "\n")
        metadata = {
            "complete_recording_plan": not allow_partial,
            "takes": [take.model_dump(mode="json") for take in takes],
        }
        (stage / "human-held-out.json").write_text(json.dumps(metadata, indent=2) + "\n")
        stage.rename(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", type=Path)
    parser.add_argument("--dataset", type=Path, default=Path("data/dataset"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    import_takes(
        args.dataset, args.labels, args.out, args.version, allow_partial=args.allow_partial
    )


if __name__ == "__main__":
    main()
