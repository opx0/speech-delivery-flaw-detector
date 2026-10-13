"""One analysis job as a small state machine.

The executor thread publishes events and the SSE generators read them, so both share this one
object. Events are append-only, which is what lets a late subscriber replay everything.
"""

import threading
from collections.abc import Callable
from enum import StrEnum

from ..contract import DoneEvent, FailedEvent, JobEvent


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


TERMINAL = frozenset({JobState.DONE, JobState.FAILED})


class IllegalTransition(RuntimeError):
    pass


class Job:
    def __init__(self, job_id: str, clock: Callable[[], float]) -> None:
        self.job_id = job_id
        self._clock = clock
        self._condition = threading.Condition()
        self._events: list[JobEvent] = []
        self._state = JobState.QUEUED
        self._finished_at: float | None = None

    @property
    def state(self) -> JobState:
        with self._condition:
            return self._state

    @property
    def finished_at(self) -> float | None:
        with self._condition:
            return self._finished_at

    def start(self) -> None:
        with self._condition:
            if self._state is not JobState.QUEUED:
                raise IllegalTransition(f"cannot start a {self._state} job")
            self._state = JobState.RUNNING

    def publish(self, event: JobEvent) -> None:
        """Append an event. A done or failed event ends the job."""
        with self._condition:
            if self._state in TERMINAL:
                raise IllegalTransition(f"{self._state} job accepts no more events")
            self._events.append(event)
            if isinstance(event, DoneEvent):
                self._state = JobState.DONE
            elif isinstance(event, FailedEvent):
                self._state = JobState.FAILED
            if self._state in TERMINAL:
                self._finished_at = self._clock()
            self._condition.notify_all()

    def events_after(self, cursor: int, timeout: float) -> tuple[JobEvent, ...]:
        """Events from index `cursor` on. Blocks up to `timeout` seconds when there are none."""
        with self._condition:
            self._condition.wait_for(lambda: len(self._events) > cursor, timeout)
            return tuple(self._events[cursor:])
