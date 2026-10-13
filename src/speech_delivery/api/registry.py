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
    ) -> None:
        self._analyzer = analyzer
        self._clock = clock
        self._max_queued = max_queued
        self._retention_s = retention_s
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="analysis")

    def submit(self, upload_dir: Path, audio_path: Path, options: AnalyzeOptions) -> Job:
        """Queue a job. It owns `upload_dir` from here on and deletes it when it ends.

        Raises QueueFull, leaving `upload_dir` to the caller.
        """
        with self._lock:
            self._forget_expired()
            queued = sum(1 for job in self._jobs.values() if job.state is JobState.QUEUED)
            if queued >= self._max_queued:
                raise QueueFull
            job = Job(f"job-{secrets.token_hex(6)}", self._clock)
            self._jobs[job.job_id] = job
            self._executor.submit(self._run, job, upload_dir, audio_path, options)
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            self._forget_expired()
            return self._jobs.get(job_id)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

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

        def progress(stage: Stage, fraction: float, message: str) -> None:
            job.publish(
                ProgressEvent(
                    job_id=job.job_id,
                    stage=stage,
                    fraction=min(max(fraction, 0.0), 1.0),
                    message=message,
                )
            )

        outcome: JobEvent
        try:
            report = self._analyzer.analyze(audio_path, options, progress)
            outcome = DoneEvent(job_id=job.job_id, report=report)
        except AnalysisError as error:
            outcome = FailedEvent(job_id=job.job_id, code=error.code, message=error.message)
        except Exception:
            logger.exception("analysis of %s failed unexpectedly", job.job_id)
            outcome = FailedEvent(
                job_id=job.job_id,
                code=ErrorCode.INTERNAL,
                message="Analysis failed unexpectedly.",
            )
        finally:
            shutil.rmtree(upload_dir, ignore_errors=True)
        job.publish(outcome)
