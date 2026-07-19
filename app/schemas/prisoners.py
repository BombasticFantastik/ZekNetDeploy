from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class PrisonerGet(BaseModel):
    id: int
    fio: str
    photo_minio_path: str
    unit_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PrisonerPatch(BaseModel):
    fio: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PrisonerUnitPatch(PrisonerPatch):
    unit_id: Optional[int] = None