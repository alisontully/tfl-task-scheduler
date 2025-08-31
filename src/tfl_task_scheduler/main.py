from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from tfl_task_scheduler import db, scheduler
from tfl_task_scheduler.api import tasks


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """App lifespan: initialize DB, start scheduler; ensure clean shutdown."""
    db.init_db()
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown()


app = FastAPI(title="TFL Task Scheduler", lifespan=lifespan)
app.include_router(tasks.router)
