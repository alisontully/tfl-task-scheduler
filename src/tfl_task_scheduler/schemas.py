# src/tfl_task_scheduler/schemas.py
from datetime import datetime
from typing import Optional, Annotated
from pydantic import BaseModel, ConfigDict, BeforeValidator

def _empty_str_to_none(v):
    if v is None:
        return None
    if isinstance(v, str) and v.strip() == "":
        return None
    return v

# Use an annotated field so "" is converted to None before datetime parsing
ScheduleTime = Annotated[Optional[datetime], BeforeValidator(_empty_str_to_none)]

class TaskBase(BaseModel):
    lines: str

class TaskCreate(TaskBase):
    schedule_time: ScheduleTime = None  # optional; "" accepted

class TaskUpdate(BaseModel):
    schedule_time: ScheduleTime = None
    lines: Optional[str] = None

class Task(TaskBase):
    id: str
    schedule_time: datetime
    result: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
