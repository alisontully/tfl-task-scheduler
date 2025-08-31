from __future__ import annotations

import json
from typing import Final

import requests
from requests import RequestException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from tfl_task_scheduler import db, models

TFL_URL_TMPL: Final[str] = "https://api.tfl.gov.uk/Line/{lines}/Disruption"
DEFAULT_HTTP_TIMEOUT: Final[float] = 15.0


def run_task(task_id: str) -> None:
    """Fetch disruptions for a task's lines and persist the result JSON.

    The task is looked up by ``task_id``. If it no longer exists (deleted),
    the function exits quietly. Network errors are captured and stored in the
    ``result`` field rather than raising, so the task always completes with a
    payload.
    """
    session: Session = db.SessionLocal()
    try:
        task = session.get(models.Task, task_id)
        if task is None:
            # Task was deleted or never existed — nothing to do
            return

        url = TFL_URL_TMPL.format(lines=task.lines)
        try:
            resp = requests.get(url, timeout=DEFAULT_HTTP_TIMEOUT)
            payload = {
                "status": resp.status_code,
                "ok": resp.ok,
                "url": url,
                "body": resp.text,
            }
        except RequestException as exc:
            payload = {
                "status": "error",
                "ok": False,
                "url": url,
                "error": type(exc).__name__,
                "message": str(exc),
            }

        # Write result; guard against concurrent delete
        rows = (
            session.query(models.Task)
            .filter(models.Task.id == task_id)
            .update({"result": json.dumps(payload)}, synchronize_session=False)
        )
        if rows:
            session.commit()
        else:
            # Someone deleted it between fetch and update
            session.rollback()
    except (SQLAlchemyError, StaleDataError):
        session.rollback()
    finally:
        session.close()
