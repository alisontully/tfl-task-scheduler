from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from tfl_task_scheduler import db, models, scheduler, schemas, worker

logger = logging.getLogger(__name__)

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
    """Normalize a CSV of line IDs.

    Split by comma, trim whitespace, lowercase, and re-join without spaces.
    """
    parts = [p.strip().lower() for p in lines_csv.split(",") if p.strip()]
    return ",".join(parts)


def _validate_lines_or_422(lines_csv: str) -> None:
    """Validate all line IDs; raise HTTP 422 if any are invalid."""
    parts = _normalize_lines(lines_csv).split(",") if lines_csv else []
    invalid = [p for p in parts if p not in ALLOWED_LINE_IDS]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid line id(s): {', '.join(invalid)}",
        )


@router.post("/", response_model=schemas.Task)
def create_task(
    task_in: schemas.TaskCreate, session: Session = Depends(db.get_session)
) -> models.Task:
    """Create a new task (runs now if ``schedule_time`` is omitted/empty)."""
    if not task_in.lines:
        raise HTTPException(status_code=422, detail="`lines` is required")

    normalized_lines = _normalize_lines(task_in.lines)
    _validate_lines_or_422(normalized_lines)

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
def list_tasks(session: Session = Depends(db.get_session)) -> List[models.Task]:
    """Return all tasks."""
    return session.query(models.Task).all()


@router.get("/{task_id}", response_model=schemas.Task, status_code=status.HTTP_200_OK)
def get_task(task_id: str, session: Session = Depends(db.get_session)) -> models.Task:
    """Return a single task by ID."""
    task = session.get(models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
def delete_task(
    task_id: str, session: Session = Depends(db.get_session)
) -> Dict[str, str]:
    """Delete a task by ID and remove any scheduled job."""
    task = session.get(models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    scheduler.remove_task(str(task.id))
    session.delete(task)
    session.commit()
    return {"message": "Task deleted"}


@router.patch("/{task_id}", response_model=schemas.Task, status_code=status.HTTP_200_OK)
def update_task(
    task_id: str,
    task_in: schemas.TaskUpdate,
    session: Session = Depends(db.get_session),
) -> models.Task:
    """Update a task's ``schedule_time`` and/or ``lines`` before it runs."""
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

    if (
        task_in.schedule_time is not None
        and task.schedule_time != task_in.schedule_time
    ):
        task.schedule_time = task_in.schedule_time
        changed = True

    if changed:
        session.commit()
        session.refresh(task)
        scheduler.reschedule_task(task, worker.run_task)

    return task


@router.delete("/", status_code=200)
def delete_all_tasks(session: Session = Depends(db.get_session)) -> Dict[str, int]:
    """Delete all tasks and clear any scheduled jobs. Returns ``{'deleted': N}``."""
    # Best-effort: clear scheduled jobs first so none fire during delete.
    try:
        scheduler.clear_all()
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("scheduler.clear_all() failed: %s", exc)

    try:
        deleted = session.query(models.Task).delete(synchronize_session=False)
        session.commit()
        return {"deleted": deleted}
    except Exception as exc:  # pylint: disable=broad-except
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"bulk delete failed: {exc}",
        ) from exc
