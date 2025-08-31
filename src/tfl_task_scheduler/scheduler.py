from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Optional, List

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

from tfl_task_scheduler import models

_scheduler: Optional[BackgroundScheduler] = None


def start() -> None:
    """Start a singleton BackgroundScheduler (idempotent)."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(
            job_defaults={"coalesce": True, "misfire_grace_time": None}
        )
        _scheduler.start()


def shutdown() -> None:
    """Shutdown the scheduler if it is running (idempotent)."""
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        finally:
            _scheduler = None


def _effective_run_time(dt: datetime) -> datetime:
    """If time is in the past, run ASAP to avoid misfires."""
    now = datetime.now()
    return dt if dt > now else now + timedelta(milliseconds=100)


def add_task(task: models.Task, func: Callable[[str], None]) -> None:
    """Schedule a one-shot job for the given task."""
    start()
    run_time = _effective_run_time(task.schedule_time or datetime.now())
    assert _scheduler is not None
    _scheduler.add_job(
        func,
        trigger=DateTrigger(run_date=run_time),
        id=task.id,
        args=[task.id],
        replace_existing=True,
    )


def reschedule_task(task: models.Task, func: Callable[[str], None]) -> None:
    """Re-schedule by replacing the job."""
    add_task(task, func)


def remove_task(task_id: str) -> None:
    if _scheduler is None:
        return
    try:
        _scheduler.remove_job(task_id)
    except Exception:
        pass  # already gone


def clear_all() -> None:
    """Remove all scheduled jobs, ignoring errors."""
    if _scheduler is None:
        return
    for job in list(_scheduler.get_jobs()):
        try:
            _scheduler.remove_job(job.id)
        except Exception:
            pass


def get_job_ids() -> List[str]:
    return [] if _scheduler is None else [j.id for j in _scheduler.get_jobs()]
