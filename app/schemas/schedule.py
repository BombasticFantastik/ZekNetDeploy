from pydantic import BaseModel
from typing import Optional
from datetime import date


class SchedulePostPutSchema(BaseModel):
    prisoner_id: int
    date: date
    status: str
    note: Optional[str] = None