"""Local report-only run journal. No uploaded audio or browser blob URLs are stored."""

import hashlib
import json
import sqlite3
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from ..contract import AnalyzeOptions, DoneEvent, FailedEvent, ProgressEvent, RubricWeights


class RunHistory:
    def __init__(self, path: Path, parameters: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.parameters = parameters
        self._lock = threading.Lock()
        with self._connection() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS runs ("
                "job_id TEXT PRIMARY KEY, created_at REAL NOT NULL, document TEXT NOT NULL)"
            )
            # Only the single-process API owns this journal. A previous crash must not leave
            # historical entries looking as though they are still processing.
            rows = db.execute(
                "SELECT job_id, document FROM runs "
                "WHERE json_extract(document, '$.status') IN ('queued', 'running')"
            ).fetchall()
            for _job_id, text in rows:
                run = json.loads(text)
                if run["status"] in ("queued", "running"):
                    run.update(status="interrupted", finished_at=time.time())
                    run["error"] = {
                        "code": "interrupted",
                        "message": (
                            "Server stopped before a terminal result was saved. "
                            "This run was not resumed."
                        ),
                    }
                    events: list[dict[str, Any]] = run["events"]
                    events.append(
                        {"at": time.time(), "elapsed_s": None, "message": run["error"]["message"]}
                    )
                    self._save(db, run)

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection]:
        with self._lock:
            db = sqlite3.connect(self.path, timeout=10)
            try:
                with db:
                    yield db
            finally:
                db.close()

    @staticmethod
    def _save(db: sqlite3.Connection, run: dict[str, Any]) -> None:
        db.execute(
            "INSERT INTO runs VALUES (?, ?, ?) "
            "ON CONFLICT(job_id) DO UPDATE SET document=excluded.document",
            (run["job_id"], run["created_at"], json.dumps(run, allow_nan=False)),
        )

    @staticmethod
    def _load(db: sqlite3.Connection, job_id: str) -> dict[str, Any] | None:
        row = db.execute("SELECT document FROM runs WHERE job_id=?", (job_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def create(self, job_id: str, audio_path: Path, filename: str, options: AnalyzeOptions) -> None:
        digest = hashlib.sha256()
        with audio_path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        now = time.time()
        run = {
            "schema_version": 1,
            "job_id": job_id,
            "created_at": now,
            "started_at": None,
            "finished_at": None,
            "elapsed_s": None,
            "status": "queued",
            "filename": filename,
            "upload_bytes": audio_path.stat().st_size,
            "audio_sha256": digest.hexdigest(),
            "audio_retained": False,
            "upload_cleanup": "pending",
            "options": options.model_dump(mode="json"),
            "parameters": {
                **self.parameters,
                "effective_weights": (options.weights or RubricWeights()).model_dump(mode="json"),
            },
            "runtime_after": None,
            "report": None,
            "error": None,
            "events": [{"at": now, "elapsed_s": 0, "message": "Upload received; analysis queued."}],
        }
        with self._connection() as db:
            self._save(db, run)

    def started(self, job_id: str) -> None:
        with self._connection() as db:
            run = self._load(db, job_id)
            if run is None:
                raise KeyError(job_id)
            now = time.time()
            run.update(status="running", started_at=now)
            run["events"].append({"at": now, "elapsed_s": 0, "message": "Analysis started."})
            self._save(db, run)

    def progress(self, event: ProgressEvent, elapsed_s: float) -> None:
        with self._connection() as db:
            run = self._load(db, event.job_id)
            if run is None:
                raise KeyError(event.job_id)
            run["events"].append(
                {
                    "at": time.time(),
                    "elapsed_s": elapsed_s,
                    "stage": event.stage.value,
                    "fraction": event.fraction,
                    "message": event.message,
                }
            )
            self._save(db, run)

    def finish(
        self,
        outcome: DoneEvent | FailedEvent,
        elapsed_s: float,
        cleanup_ok: bool,
        runtime: dict[str, Any],
    ) -> None:
        with self._connection() as db:
            run = self._load(db, outcome.job_id)
            if run is None:
                raise KeyError(outcome.job_id)
            now = time.time()
            done = isinstance(outcome, DoneEvent)
            run.update(
                status="done" if done else "failed",
                finished_at=now,
                elapsed_s=elapsed_s,
                upload_cleanup="removed" if cleanup_ok else "incomplete",
                runtime_after=runtime,
            )
            if done:
                run["report"] = outcome.report.model_dump(mode="json")
            else:
                run["error"] = {"code": outcome.code.value, "message": outcome.message}
            run["events"].append(
                {
                    "at": now,
                    "elapsed_s": elapsed_s,
                    "message": "Analysis complete; report saved." if done else outcome.message,
                }
            )
            run["events"].append(
                {
                    "at": now,
                    "elapsed_s": elapsed_s,
                    "message": "Temporary upload removed."
                    if cleanup_ok
                    else "Upload cleanup incomplete; needs attention.",
                }
            )
            self._save(db, run)

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._connection() as db:
            return self._load(db, job_id)

    def listing(self, limit: int, offset: int) -> dict[str, Any]:
        with self._connection() as db:
            counts = {
                status: 0 for status in ("queued", "running", "done", "failed", "interrupted")
            }
            for status, count in db.execute(
                "SELECT json_extract(document, '$.status'), COUNT(*) FROM runs GROUP BY 1"
            ):
                counts[status] = count
            rows = db.execute(
                "SELECT document FROM runs ORDER BY created_at DESC, job_id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        runs: list[dict[str, Any]] = []
        for (text,) in rows:
            run = json.loads(text)
            report = run.get("report")
            runs.append(
                {
                    **{
                        key: run[key]
                        for key in ("job_id", "filename", "created_at", "status", "elapsed_s")
                    },
                    "overall": report["overall"] if report else None,
                    "findings": len(report["regions"]) if report else None,
                    "reference_basis": report["reference"]["basis"] if report else None,
                }
            )
        return {
            "runs": runs,
            "counts": counts,
            "total": sum(counts.values()),
            "offset": offset,
            "limit": limit,
        }
