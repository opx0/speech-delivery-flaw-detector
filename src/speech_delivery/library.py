"""The dataset on disk: a manifest plus the FLAC files it describes.

Everything downstream reads the dataset through `Library`, so the manifest's hashes are checked
in one place and no package builds its own paths.
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .audio import Audio, read_flac, sha256_file
from .contract import (
    FLAW_SPECS,
    Category,
    ClipLabel,
    ClipRole,
    DatasetManifest,
    DemoClip,
    LibraryEntry,
    LibraryListing,
    Split,
    TextRecord,
)
from .text import similarity

MANIFEST_NAME = "manifest.json"
TRANSCRIPT_MATCH_THRESHOLD = 0.9
DEMO_LEVEL = 3


class DatasetIntegrityError(RuntimeError):
    """A file on disk does not match what the manifest promises."""


@dataclass(frozen=True, slots=True)
class Library:
    root: Path
    manifest: DatasetManifest

    @classmethod
    def load(cls, root: Path) -> "Library":
        manifest = DatasetManifest.model_validate_json((root / MANIFEST_NAME).read_text("utf-8"))
        return cls(root=root, manifest=manifest)

    def clip(self, clip_id: str) -> ClipLabel:
        for clip in self.manifest.clips:
            if clip.id == clip_id:
                return clip
        raise KeyError(clip_id)

    def text(self, text_id: str) -> TextRecord:
        for text in self.manifest.texts:
            if text.id == text_id:
                return text
        raise KeyError(text_id)

    def clips(
        self,
        *,
        role: ClipRole | Iterable[ClipRole] | None = None,
        split: Split | None = None,
        text_id: str | None = None,
    ) -> tuple[ClipLabel, ...]:
        roles = {role} if isinstance(role, ClipRole) else set(role) if role is not None else None
        return tuple(
            clip
            for clip in self.manifest.clips
            if (roles is None or clip.role in roles)
            and (split is None or clip.split is split)
            and (text_id is None or clip.text_id == text_id)
        )

    def gold_for(self, text_id: str) -> ClipLabel:
        (gold,) = self.clips(role=ClipRole.GOLD, text_id=text_id)
        return gold

    def audio(self, clip_id: str) -> Audio:
        """Read a clip, refusing it if its bytes differ from the manifest."""
        clip = self.clip(clip_id)
        path = self.root / clip.audio.path
        if sha256_file(path) != clip.audio.sha256:
            raise DatasetIntegrityError(f"{clip.audio.path} does not match its manifest hash")
        return read_flac(path)

    def match_text(self, transcript: str) -> TextRecord | None:
        """The library text a transcript reads, or None when it is not in the library."""
        scored = [(similarity(transcript, text.transcript), text) for text in self.contrast_texts()]
        if not scored:
            return None
        score, best = max(scored, key=lambda pair: pair[0])
        return best if score >= TRANSCRIPT_MATCH_THRESHOLD else None

    def contrast_texts(self) -> tuple[TextRecord, ...]:
        """Texts that have a gold baseline to compare against."""
        return tuple(
            text
            for text in self.manifest.texts
            if text.category is not Category.EXTEMPORANEOUS
            and self.clips(role=ClipRole.GOLD, text_id=text.id)
        )

    def entries(self) -> tuple[LibraryEntry, ...]:
        return tuple(
            LibraryEntry(
                text_id=text.id,
                title=text.title,
                category=text.category,
                transcript=text.transcript,
                baseline_clip_id=gold.id,
                baseline_audio_url=f"/api/audio/{gold.id}",
                duration_s=gold.audio.duration_s,
            )
            for text in self.contrast_texts()
            for gold in [self.gold_for(text.id)]
        )

    def demos(self) -> tuple[DemoClip, ...]:
        """One clip per flaw kind at level 3 for every library text, plus the clean control.

        Level 3 is audible without being absurd, so a visitor can hear what the detector flags.
        """
        demos: list[DemoClip] = []
        for text in self.contrast_texts():
            for clip in self.clips(role=ClipRole.CONTROL, text_id=text.id):
                demos.append(
                    DemoClip(
                        clip_id=clip.id,
                        text_id=text.id,
                        title=f"{text.title}: clean control",
                        description="The gold delivery passed through the same pipeline with no "
                        "flaw. The detector should find nothing.",
                        audio_url=f"/api/audio/{clip.id}",
                        flaw_kinds=(),
                        level=0,
                    )
                )
            for clip in self.clips(role=ClipRole.FLAWED, text_id=text.id):
                kinds = tuple(dict.fromkeys(flaw.kind for flaw in clip.flaws))
                levels = Counter(flaw.level for flaw in clip.flaws)
                if len(kinds) != 1 or set(levels) != {DEMO_LEVEL}:
                    continue
                label = FLAW_SPECS[kinds[0]].label
                demos.append(
                    DemoClip(
                        clip_id=clip.id,
                        text_id=text.id,
                        title=f"{text.title}: {label.lower()}",
                        description=f"{label} injected into {len(clip.flaws)} regions at "
                        f"severity {DEMO_LEVEL} of 4.",
                        audio_url=f"/api/audio/{clip.id}",
                        flaw_kinds=kinds,
                        level=DEMO_LEVEL,
                    )
                )
        return tuple(demos)

    def listing(self) -> LibraryListing:
        return LibraryListing(entries=self.entries(), demos=self.demos())
