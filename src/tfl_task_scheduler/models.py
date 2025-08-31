from __future__ import annotations

from sqlalchemy import Column, DateTime, String, Text

from tfl_task_scheduler.db import Base


class Task(Base):  # pylint: disable=too-few-public-methods
    """Task row representing a scheduled TFL query."""

    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    schedule_time = Column(DateTime, nullable=False)
    lines = Column(String, nullable=False)
    result = Column(Text, nullable=True)

    def __repr__(self) -> str:
        """Return a concise debug representation."""
        return (
            f"Task(id={self.id!r}, schedule_time={self.schedule_time!r}, "
            f"lines={self.lines!r})"
        )
