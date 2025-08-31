from datetime import datetime, timedelta

from tfl_task_scheduler import models, scheduler


def test_scheduler_add_and_remove(db_session):
    task = models.Task(
        id="test-task",
        schedule_time=datetime.now() + timedelta(seconds=1),
        lines="central",
        result=None,
    )

    scheduler.add_task(task, lambda task_id: None)

    job_ids = scheduler.get_job_ids()
    assert "test-task" in job_ids

    scheduler.remove_task("test-task")
    job_ids = scheduler.get_job_ids()
    assert "test-task" not in job_ids
