from sqlalchemy import Column, String, DateTime, Text
from tfl_task_scheduler.db import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    schedule_time = Column(DateTime, nullable=False)
    lines = Column(String, nullable=False)
    result = Column(Text, nullable=True)
