from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Optional, cast

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

from tfl_task_scheduler import models


class _SchedulerHolder:  # pylint: disable=too-few-public-methods
    """Lightweight holder to avoid using module-level `global` statements."""

    instance: Optional[BackgroundScheduler] = None


_holder = _SchedulerHolder()


def start() -> None:
    """Start a singleton BackgroundScheduler (idempotent)."""
    if _holder.instance is None:
        _holder.instance = BackgroundScheduler(
            job_defaults={"coalesce": True, "misfire_grace_time": None}
        )
        _holder.instance.start()


def shutdown() -> None:
    """Shutdown the scheduler if it is running (idempotent)."""
    if _holder.instance is not None:
        _holder.instance.shutdown(wait=False)
        _holder.instance = None


def _effective_run_time(dt: datetime) -> datetime:
    """Return a run time that's now+ε if the provided time is in the past."""
    now = datetime.now()
    return dt if dt > now else now + timedelta(milliseconds=100)


def add_task(task: models.Task, func: Callable[[str], None]) -> None:
    """Schedule a one-shot job for the given task."""
    start()
    run_time = _effective_run_time(cast(datetime, task.schedule_time) or datetime.now())
    assert _holder.instance is not None
    _holder.instance.add_job(
        func,
        trigger=DateTrigger(run_date=run_time),
        id=task.id,
        args=[task.id],
        replace_existing=True,
    )


def reschedule_task(task: models.Task, func: Callable[[str], None]) -> None:
    """Re-schedule the job by replacing it with the new time/args."""
    add_task(task, func)


def remove_task(task_id: str) -> None:
    """Remove a scheduled job by id; ignore if it doesn't exist."""
    if _holder.instance is None:
        return
    try:
        _holder.instance.remove_job(task_id)
    except JobLookupError:
        # Job already gone; nothing to do.
        return


def clear_all() -> None:
    """Remove all scheduled jobs."""
    if _holder.instance is None:
        return
    _holder.instance.remove_all_jobs()


def get_job_ids() -> list[str]:
    """Return the IDs of all currently scheduled jobs."""
    if _holder.instance is None:
        return []
    return [job.id for job in _holder.instance.get_jobs()]
