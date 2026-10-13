import pytest

from speech_delivery.api.job import IllegalTransition, Job, JobState
from speech_delivery.contract import ErrorCode, FailedEvent, ProgressEvent, Stage


def _progress() -> ProgressEvent:
    return ProgressEvent(job_id="job-a", stage=Stage.DECODE, fraction=0.5, message="m")


def _failed() -> FailedEvent:
    return FailedEvent(job_id="job-a", code=ErrorCode.INTERNAL, message="x")


def test_a_job_moves_from_queued_to_running_to_failed_and_stamps_its_finish_time() -> None:
    job = Job("job-a", clock=lambda: 42.0)
    assert (job.state, job.finished_at) == (JobState.QUEUED, None)

    job.start()
    job.publish(_progress())
    assert job.state is JobState.RUNNING

    job.publish(_failed())
    assert (job.state, job.finished_at) == (JobState.FAILED, 42.0)


def test_a_finished_job_refuses_more_events_and_a_running_job_refuses_a_second_start() -> None:
    job = Job("job-a", clock=lambda: 0.0)
    job.start()
    with pytest.raises(IllegalTransition):
        job.start()
    job.publish(_failed())

    with pytest.raises(IllegalTransition):
        job.publish(_progress())


def test_events_after_a_cursor_return_only_the_new_ones_and_time_out_when_there_are_none() -> None:
    job = Job("job-a", clock=lambda: 0.0)
    job.start()
    first = _progress()
    job.publish(first)

    assert job.events_after(0, 0.01) == (first,)
    assert job.events_after(1, 0.01) == ()
