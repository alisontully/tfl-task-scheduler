from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict


def _empty_str_to_none(v: object) -> object:
    """Coerce empty strings to None (used before datetime parsing)."""
    if v is None:
        return None
    if isinstance(v, str) and v.strip() == "":
        return None
    return v


# Use an annotated field so "" is converted to None before datetime parsing
ScheduleTime = Annotated[Optional[datetime], BeforeValidator(_empty_str_to_none)]


class TaskBase(BaseModel):
    """Common fields shared by task payloads."""

    lines: str


class TaskCreate(TaskBase):
    """Payload to create a task."""

    # Optional; "" is accepted and becomes None -> "run now"
    schedule_time: ScheduleTime = None


class TaskUpdate(BaseModel):
    """Partial update payload for an existing task."""

    schedule_time: ScheduleTime = None
    lines: Optional[str] = None


class Task(TaskBase):
    """Response model for a task (as stored in the database)."""

    id: str
    schedule_time: datetime
    result: Optional[str] = None

    # Enable ORM serialization for SQLAlchemy models
    model_config = ConfigDict(from_attributes=True)
