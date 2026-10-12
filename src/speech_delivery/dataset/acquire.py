"""Download source recordings and cache cleaned source transcripts."""

import hashlib
import json
import re
import sys
from html import unescape
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse

import httpx

from speech_delivery.contract.dataset import SourceRecord, TextRecord
from speech_delivery.dataset.registry import SOURCES, TEXTS

_USER_AGENT = "speech-delivery-flaw-detector/0.1 (dataset acquisition)"
_TAG = re.compile(r"<[^>]+>")
_FOOTNOTE = re.compile(r"\[\s*(?:\d+|[a-z]+)\s*\]", re.IGNORECASE)
_SPACE = re.compile(r"[\t\r\n ]+")


def _filename(source: SourceRecord) -> str:
    suffix = Path(urlparse(source.audio_url).path).suffix or ".audio"
    return f"{source.id}{suffix}"


def _checksums_path(raw_dir: Path) -> Path:
    return raw_dir / "checksums.json"


def _load_checksums(raw_dir: Path) -> dict[str, str]:
    path = _checksums_path(raw_dir)
    return json.loads(path.read_text()) if path.exists() else {}


def _write_checksums(raw_dir: Path, checksums: dict[str, str]) -> None:
    _checksums_path(raw_dir).write_text(json.dumps(checksums, indent=2, sort_keys=True) + "\n")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(source: SourceRecord, raw_dir: Path, *, force: bool = False) -> Path:
    """Atomically download one source and record its content digest.

    A prior digest is authoritative: a remote replacement is refused unless ``force`` is set.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    destination = raw_dir / _filename(source)
    checksums = _load_checksums(raw_dir)
    known = checksums.get(source.id)
    if destination.exists() and known == _sha256(destination):
        return destination
    if destination.exists() and known is not None and not force:
        raise ValueError(f"{source.id}: local file differs from recorded checksum")
    with httpx.stream(
        "GET",
        source.audio_url,
        headers={"User-Agent": _USER_AGENT},
        follow_redirects=True,
        timeout=60,
    ) as response:
        response.raise_for_status()
        with NamedTemporaryFile(dir=raw_dir, prefix=f".{source.id}.", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            for block in response.iter_bytes(1 << 20):
                temporary.write(block)
    try:
        digest = _sha256(temporary_path)
        if known is not None and known != digest and not force:
            raise ValueError(f"{source.id}: remote file differs from recorded checksum")
        temporary_path.replace(destination)
    finally:
        temporary_path.unlink(missing_ok=True)
    checksums[source.id] = digest
    _write_checksums(raw_dir, checksums)
    return destination


def clean_transcript(content: str) -> str:
    """Convert a source HTML/plain-text excerpt to readable, single-spaced prose."""
    text = unescape(_TAG.sub(" ", content))
    text = _FOOTNOTE.sub("", text)
    text = re.sub(r"\b(?:\d+|[IVXLCDM]+)\s*\n", "", text)
    return _SPACE.sub(" ", text).strip()


def fetch_transcript(text: TextRecord, work_dir: Path) -> Path:
    """Fetch and cache a cleaned transcript under ``work_dir/transcripts``."""
    output = work_dir / "transcripts" / f"{text.id}.txt"
    if output.exists():
        return output
    output.parent.mkdir(parents=True, exist_ok=True)
    response = httpx.get(
        text.transcript_url, headers={"User-Agent": _USER_AGENT}, follow_redirects=True, timeout=30
    )
    response.raise_for_status()
    cleaned = clean_transcript(response.text)
    if not cleaned:
        raise ValueError(f"{text.id}: transcript URL yielded no readable text")
    with NamedTemporaryFile(
        dir=output.parent, prefix=f".{text.id}.", mode="w", encoding="utf-8", delete=False
    ) as temporary:
        temporary.write(cleaned + "\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(output)
    return output


def main() -> None:
    """Fetch the complete frozen registry, reporting all independent failures."""
    raw_dir = Path("data/raw")
    work_dir = Path("data/work")
    failures: list[str] = []
    print(f"{'kind':10} {'id':45} result")
    for source in SOURCES:
        try:
            print(f"{'audio':10} {source.id:45} {fetch(source, raw_dir)}")
        except (httpx.HTTPError, OSError, ValueError) as error:
            failures.append(f"{source.id}: {error}")
            print(f"{'audio':10} {source.id:45} FAILED: {error}")
    for text in TEXTS:
        try:
            print(f"{'transcript':10} {text.id:45} {fetch_transcript(text, work_dir)}")
        except (httpx.HTTPError, OSError, ValueError) as error:
            failures.append(f"{text.id}: {error}")
            print(f"{'transcript':10} {text.id:45} FAILED: {error}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
