from __future__ import annotations

import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from tfl_task_scheduler import db, models, schemas, scheduler, worker

router = APIRouter(prefix="/tasks", tags=["tasks"])

# Allowed Tube line IDs for validation
ALLOWED_LINE_IDS = {
    "bakerloo",
    "central",
    "circle",
    "district",
    "hammersmith-city",
    "jubilee",
    "metropolitan",
    "northern",
    "piccadilly",
    "victoria",
    "waterloo-city",
}


def _normalize_lines(lines_csv: str) -> str:
    """
    Normalize a comma-separated list of TFL line IDs:
    - split by comma
    - trim whitespace
    - lowercase ids
    - re-join with commas (no spaces)
    """
    parts = [p.strip().lower() for p in lines_csv.split(",") if p.strip()]
    return ",".join(parts)


def _validate_lines_or_422(lines_csv: str) -> None:
    """
    Validate all line IDs; raise 422 if any are invalid.
    """
    parts = _normalize_lines(lines_csv).split(",") if lines_csv else []
    invalid = [p for p in parts if p not in ALLOWED_LINE_IDS]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid line id(s): {', '.join(invalid)}",
        )


@router.post("/", response_model=schemas.Task)
def create_task(task_in: schemas.TaskCreate, session: Session = Depends(db.get_session)):
    if not task_in.lines:
        raise HTTPException(status_code=422, detail="`lines` is required")

    normalized_lines = _normalize_lines(task_in.lines)
    _validate_lines_or_422(normalized_lines)

    # Missing or "" schedule_time => run now
    when = task_in.schedule_time or datetime.now()

    task = models.Task(
        id=str(uuid.uuid4()),
        schedule_time=when,
        lines=normalized_lines,
        result=None,
    )
    session.add(task)
    session.commit()
    session.refresh(task)

    scheduler.add_task(task, worker.run_task)
    return task


@router.get("/", response_model=List[schemas.Task], status_code=status.HTTP_200_OK)
def list_tasks(session: Session = Depends(db.get_session)) -> List[schemas.Task]:
    """
    List all tasks.
    """
    return session.query(models.Task).all()


@router.get("/{task_id}", response_model=schemas.Task, status_code=status.HTTP_200_OK)
def get_task(task_id: str, session: Session = Depends(db.get_session)) -> schemas.Task:
    """
    Get a single task by id.
    """
    task = session.get(models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
def delete_task(task_id: str, session: Session = Depends(db.get_session)) -> dict:
    """
    Delete a task by id and remove any scheduled job.
    """
    task = session.get(models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    scheduler.remove_task(task.id)
    session.delete(task)
    session.commit()
    return {"message": "Task deleted"}


@router.patch("/{task_id}", response_model=schemas.Task, status_code=status.HTTP_200_OK)
def update_task(
    task_id: str,
    task_in: schemas.TaskUpdate,
    session: Session = Depends(db.get_session),
) -> schemas.Task:
    """
    Update an existing task's `schedule_time` and/or `lines`.

    Rules:
    - If the task already produced a result (i.e., has run), it cannot be updated.
    - Lines are validated; time can be moved to past (will run ASAP).
    - Any change triggers rescheduling.
    """
    task = session.get(models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.result is not None:
        raise HTTPException(
            status_code=400,
            detail="Cannot update a task that has already run",
        )

    changed = False

    if task_in.lines is not None:
        normalized_lines = _normalize_lines(task_in.lines)
        _validate_lines_or_422(normalized_lines)
        if normalized_lines != task.lines:
            task.lines = normalized_lines
            changed = True

    if task_in.schedule_time is not None:
        if task.schedule_time != task_in.schedule_time:
            task.schedule_time = task_in.schedule_time
            changed = True

    if changed:
        session.commit()
        session.refresh(task)
        scheduler.reschedule_task(task, worker.run_task)

    return task

@router.delete("/", status_code=200)
def delete_all_tasks(session: Session = Depends(db.get_session)):
    """
    Delete all tasks and clear any scheduled jobs.
    Returns {"deleted": <count>}.
    """
    # Best-effort: clear scheduled jobs first so none fire during delete
    try:
        scheduler.clear_all()
    except Exception as e:  # don't block deletes if clearing fails
        print(f"[delete_all] scheduler.clear_all() failed: {e}")

    try:
        deleted = session.query(models.Task).delete(synchronize_session=False)
        session.commit()
        return {"deleted": deleted}
    except Exception as e:
        session.rollback()
        # surface the reason instead of a bare 500
        raise HTTPException(status_code=500, detail=f"bulk delete failed: {e}")