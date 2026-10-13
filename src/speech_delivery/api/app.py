"""The HTTP surface: library, demo audio, upload jobs and their event stream."""

import shutil
import time
from collections.abc import AsyncGenerator, Callable, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import TypeAdapter, ValidationError

from ..analysis.protocol import Analyzer
from ..contract import (
    AnalyzeOptions,
    ClipRole,
    JobCreated,
    JobEvent,
    LibraryListing,
)
from ..contract.jobs import MAX_UPLOAD_BYTES
from ..library import Library
from .job import Job
from .registry import MAX_QUEUED, JobRegistry, QueueFull
from .upload import BodyLimit, UploadTooLarge, save_upload

HEARTBEAT_S = 15.0
SERVED_ROLES = frozenset({ClipRole.GOLD, ClipRole.CONTROL, ClipRole.FLAWED})
EVENT_ADAPTER: TypeAdapter[JobEvent] = TypeAdapter(JobEvent)


def create_app(
    library: Library,
    analyzer: Analyzer,
    web_dist: Path | None = None,
    *,
    max_upload_bytes: int = MAX_UPLOAD_BYTES,
    max_queued: int = MAX_QUEUED,
    heartbeat_s: float = HEARTBEAT_S,
    clock: Callable[[], float] = time.monotonic,
) -> FastAPI:
    registry = JobRegistry(analyzer, clock=clock, max_queued=max_queued)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        yield
        registry.shutdown()

    app = FastAPI(
        title="Speech delivery flaw detector", lifespan=lifespan, docs_url=None, redoc_url=None
    )
    app.add_middleware(BodyLimit, path="/api/jobs", limit=max_upload_bytes)

    @app.get("/api/library")
    def get_library() -> LibraryListing:
        return library.listing()

    @app.get("/api/audio/{clip_id}")
    def get_audio(clip_id: str) -> FileResponse:
        try:
            clip = library.clip(clip_id)
        except KeyError:
            raise HTTPException(404, "No such clip.") from None
        root = library.root.resolve()
        path = (root / clip.audio.path).resolve()
        if clip.role not in SERVED_ROLES or not path.is_relative_to(root) or not path.is_file():
            raise HTTPException(404, "No such clip.")
        return FileResponse(path, media_type="audio/flac")

    @app.post("/api/jobs", status_code=202)
    def create_job(
        audio: Annotated[UploadFile, File()], options: Annotated[str, Form()]
    ) -> JobCreated:
        try:
            parsed = AnalyzeOptions.model_validate_json(options)
        except ValidationError as error:
            raise HTTPException(422, _describe(error)) from None
        try:
            directory, path = save_upload(audio, max_upload_bytes)
        except UploadTooLarge:
            raise HTTPException(413, "The upload is too large.") from None
        try:
            job = registry.submit(directory, path, parsed)
        except QueueFull:
            shutil.rmtree(directory, ignore_errors=True)
            raise HTTPException(429, "Too many analyses are waiting. Try again shortly.") from None
        return JobCreated(job_id=job.job_id)

    @app.get("/api/jobs/{job_id}/events")
    def job_events(job_id: str) -> StreamingResponse:
        job = registry.get(job_id)
        if job is None:
            raise HTTPException(404, "No such job.")
        return StreamingResponse(
            _stream(job, heartbeat_s),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    if web_dist is not None and web_dist.is_dir():
        _mount_spa(app, web_dist.resolve())

    return app


def _describe(error: ValidationError) -> str:
    return "Invalid options: " + "; ".join(
        f"{'.'.join(str(part) for part in item['loc']) or 'options'}: {item['msg']}"
        for item in error.errors(include_url=False)
    )


def _stream(job: Job, heartbeat_s: float) -> Iterator[str]:
    cursor = 0
    while True:
        events = job.events_after(cursor, heartbeat_s)
        if not events:
            yield ": heartbeat\n\n"
            continue
        for event in events:
            yield f"data: {EVENT_ADAPTER.dump_json(event).decode()}\n\n"
        cursor += len(events)
        if events[-1].type != "progress":
            return


def _mount_spa(app: FastAPI, web_dist: Path) -> None:
    index = web_dist / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "Not found.")
        candidate = (web_dist / path).resolve()
        if candidate.is_relative_to(web_dist) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)
