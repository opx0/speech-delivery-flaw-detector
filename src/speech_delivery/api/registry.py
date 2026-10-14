"""The jobs in flight and recently finished, and the bounded pool that runs them."""

import logging
import secrets
import shutil
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..analysis.protocol import AnalysisError, Analyzer
from ..contract import (
    AnalyzeOptions,
    DoneEvent,
    ErrorCode,
    FailedEvent,
    JobEvent,
    ProgressEvent,
    Stage,
)
from .history import RunHistory
from .job import Job, JobState

logger = logging.getLogger(__name__)

WORKERS = 2
MAX_QUEUED = 8
RETENTION_S = 30 * 60


class QueueFull(Exception):
    pass


class JobRegistry:
    def __init__(
        self,
        analyzer: Analyzer,
        *,
        clock: Callable[[], float],
        workers: int = WORKERS,
        max_queued: int = MAX_QUEUED,
        retention_s: float = RETENTION_S,
        history: RunHistory | None = None,
    ) -> None:
        self._analyzer = analyzer
        self._clock = clock
        self._max_queued = max_queued
        self._retention_s = retention_s
        self._history = history
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="analysis")

    def submit(
        self,
        upload_dir: Path,
        audio_path: Path,
        options: AnalyzeOptions,
        filename: str = "Recording",
    ) -> Job:
        """Queue a job. It owns `upload_dir` from here on and deletes it when it ends.

        Raises QueueFull, leaving `upload_dir` to the caller.
        """
        with self._lock:
            self._forget_expired()
            queued = sum(1 for job in self._jobs.values() if job.state is JobState.QUEUED)
            if queued >= self._max_queued:
                raise QueueFull
            job = Job(f"job-{secrets.token_hex(6)}", self._clock)
            if self._history:
                self._history.create(job.job_id, audio_path, filename, options)
            self._jobs[job.job_id] = job
            logger.info("job=%s | QUEUED | upload_bytes=%d", job.job_id, audio_path.stat().st_size)
            self._executor.submit(self._run, job, upload_dir, audio_path, options)
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            self._forget_expired()
            return self._jobs.get(job_id)

    def shutdown(self) -> None:
        # Drain admitted jobs so their reports/failures are journaled and uploads removed.
        self._executor.shutdown(wait=True)

    def _forget_expired(self) -> None:
        now = self._clock()
        expired = [
            job_id
            for job_id, job in self._jobs.items()
            if (finished := job.finished_at) is not None and now - finished > self._retention_s
        ]
        for job_id in expired:
            del self._jobs[job_id]

    def _run(self, job: Job, upload_dir: Path, audio_path: Path, options: AnalyzeOptions) -> None:
        job.start()
        started = self._clock()
        logger.info("job=%s | STARTED | running real audio analysis", job.job_id)

        def progress(stage: Stage, fraction: float, message: str) -> None:
            logger.info(
                "job=%s | %s | stage_progress=%.0f%% | elapsed=%.2fs",
                job.job_id,
                stage.value.upper(),
                min(max(fraction, 0.0), 1.0) * 100,
                self._clock() - started,
            )
            event = ProgressEvent(
                job_id=job.job_id,
                stage=stage,
                fraction=min(max(fraction, 0.0), 1.0),
                message=message,
            )
            if self._history:
                self._history.progress(event, self._clock() - started)
            job.publish(event)

        outcome: JobEvent
        try:
            if self._history:
                self._history.started(job.job_id)
            report = self._analyzer.analyze(audio_path, options, progress)
            logger.info(
                "job=%s | COMPLETE | elapsed=%.2fs audio=%.2fs words=%d "
                "findings=%d delivery_score=%.1f",
                job.job_id,
                self._clock() - started,
                report.participant.duration_s,
                len(report.words.words),
                len(report.regions),
                report.overall,
            )
            for region in report.regions:
                logger.info(
                    "job=%s | FINDING | kind=%s start=%.2fs end=%.2fs observed=%.4f unit=%s",
                    job.job_id,
                    region.kind.value,
                    region.start,
                    region.end,
                    region.deviation.observed,
                    region.deviation.unit,
                )
            outcome = DoneEvent(job_id=job.job_id, report=report)
        except AnalysisError as error:
            logger.warning(
                "job=%s | FAILED | code=%s elapsed=%.2fs",
                job.job_id,
                error.code.value,
                self._clock() - started,
            )
            outcome = FailedEvent(job_id=job.job_id, code=error.code, message=error.message)
        except Exception as error:
            logger.error(
                "job=%s | FAILED | unexpected=%s elapsed=%.2fs",
                job.job_id,
                type(error).__name__,
                self._clock() - started,
            )
            outcome = FailedEvent(
                job_id=job.job_id,
                code=ErrorCode.INTERNAL,
                message="Analysis failed unexpectedly.",
            )
        finally:
            shutil.rmtree(upload_dir, ignore_errors=True)
            if upload_dir.exists():
                logger.warning(
                    "job=%s | CLEANUP INCOMPLETE | temporary upload needs attention", job.job_id
                )
            else:
                logger.info("job=%s | CLEANUP | temporary upload removed", job.job_id)
        if self._history:
            from ..analysis.align import runtime_info

            try:
                self._history.finish(
                    outcome, self._clock() - started, not upload_dir.exists(), runtime_info()
                )
            except Exception:
                logger.error(
                    "job=%s | HISTORY SAVE FAILED | live result still available", job.job_id
                )
        job.publish(outcome)
