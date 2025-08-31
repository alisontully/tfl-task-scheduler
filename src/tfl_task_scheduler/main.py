from contextlib import asynccontextmanager
from fastapi import FastAPI

from tfl_task_scheduler import db, scheduler
from tfl_task_scheduler.api import tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown()


app = FastAPI(title="TFL Task Scheduler", lifespan=lifespan)
app.include_router(tasks.router)
