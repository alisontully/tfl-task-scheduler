from __future__ import annotations

from datetime import datetime, timedelta

from tfl_task_scheduler import models, scheduler


def test_create_and_get_task(client):
    r = client.post("/tasks/", json={"lines": "victoria"})
    assert r.status_code == 200
    tid = r.json()["id"]

    r2 = client.get(f"/tasks/{tid}")
    assert r2.status_code == 200
    data = r2.json()
    assert data["id"] == tid
    assert data["lines"] == "victoria"
    assert data["result"] is None


def test_create_accepts_empty_schedule_time(client):
    r = client.post("/tasks/", json={"schedule_time": "", "lines": "victoria"})
    assert r.status_code == 200
    data = r.json()
    # server fills in current time when empty/missing
    assert isinstance(data["schedule_time"], str)
    assert data["schedule_time"]  # non-empty ISO string


def test_create_normalizes_lines(client):
    # Mixed case and spaces should normalize to lowercase, comma-joined
    r = client.post("/tasks/", json={"lines": "  Victoria ,  CENTRAL  "})
    assert r.status_code == 200
    assert r.json()["lines"] == "victoria,central"


def test_create_invalid_line_returns_422(client):
    r = client.post("/tasks/", json={"lines": "not-a-line"})
    assert r.status_code == 422
    assert "Invalid line id" in r.text


def test_patch_future_updates_lines_and_time(client):
    # Create a task in the near future
    when = (datetime.now() + timedelta(seconds=30)).isoformat(timespec="seconds")
    r = client.post("/tasks/", json={"schedule_time": when, "lines": "victoria"})
    assert r.status_code == 200
    tid = r.json()["id"]

    # Update lines only
    r2 = client.patch(f"/tasks/{tid}", json={"lines": "central"})
    assert r2.status_code == 200
    assert r2.json()["lines"] == "central"

    # Update schedule_time (further in future)
    when2 = (datetime.now() + timedelta(minutes=5)).isoformat(timespec="seconds")
    r3 = client.patch(f"/tasks/{tid}", json={"schedule_time": when2})
    assert r3.status_code == 200
    assert r3.json()["schedule_time"].startswith(when2)

    # (Optional) a job should still exist for this task id
    assert tid in set(scheduler.get_job_ids())


def test_patch_after_run_forbidden(client, db_session):
    # Create "now" task
    r = client.post("/tasks/", json={"lines": "victoria"})
    assert r.status_code == 200
    tid = r.json()["id"]

    # Mark it as "already run" by setting a non-null result directly in DB
    task = db_session.get(models.Task, tid)
    task.result = "{}"
    db_session.commit()

    # Now PATCH should be rejected (strict policy: can't update after run)
    r2 = client.patch(f"/tasks/{tid}", json={"lines": "central"})
    assert r2.status_code == 400
    assert "already run" in r2.text


def test_delete_task_and_delete_all(client):
    # Create two tasks
    r1 = client.post("/tasks/", json={"lines": "victoria"})
    r2 = client.post("/tasks/", json={"lines": "central"})
    t1 = r1.json()["id"]
    t2 = r2.json()["id"]

    # Delete first
    del1 = client.delete(f"/tasks/{t1}")
    assert del1.status_code == 200

    # Verify first is gone, second remains
    g1 = client.get(f"/tasks/{t1}")
    assert g1.status_code == 404
    g2 = client.get(f"/tasks/{t2}")
    assert g2.status_code == 200

    # Delete all
    da = client.delete("/tasks/")
    assert da.status_code == 200
    # Both should now be gone
    g1b = client.get(f"/tasks/{t1}")
    g2b = client.get(f"/tasks/{t2}")
    assert g1b.status_code == 404
    assert g2b.status_code == 404
