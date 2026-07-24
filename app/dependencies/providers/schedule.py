from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories import ScheduleRepository
from app.services import ScheduleService


def get_schedule_repo(db: AsyncSession = Depends(get_db)) -> ScheduleRepository:
    return ScheduleRepository(db)


def get_schedule_service(
        repo: ScheduleRepository = Depends(get_schedule_repo)
) -> ScheduleService:
    return ScheduleService(repo)