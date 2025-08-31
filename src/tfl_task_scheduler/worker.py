from __future__ import annotations

import json
import requests
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import StaleDataError

from tfl_task_scheduler import db, models

TFL_URL_TMPL = "https://api.tfl.gov.uk/Line/{lines}/Disruption"

def run_task(task_id: str) -> None:
    session: Session = db.SessionLocal()
    task = None
    try:
        task = session.get(models.Task, task_id)
        if task is None:
            # Task was deleted or never existed — nothing to do
            return

        url = TFL_URL_TMPL.format(lines=task.lines)
        try:
            resp = requests.get(url, timeout=15)
            payload = {
                "status": resp.status_code,
                "ok": resp.ok,
                "url": url,
                "body": resp.text,
            }
        except Exception as exc:
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
            session.rollback()  # someone deleted it in the meantime
    except (SQLAlchemyError, StaleDataError):
        session.rollback()
    finally:
        session.close()
