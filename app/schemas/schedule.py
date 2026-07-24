from pydantic import BaseModel
from typing import Optional
from datetime import date


class SchedulePostSchema(BaseModel):
    prisoner_id: int
    date_from: date
    date_to: date
    status: str
    note: Optional[str] = None


class SchedulePatchSchema(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    status: Optional[str] = None
    note: Optional[str] = None