from fastapi import Depends

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

from app.repositories import UnitRepository
from app.services import UnitService


def get_units_repo(db: AsyncSession = Depends(get_db)):
    return UnitRepository(db)


def get_units_service(
    repo: UnitRepository = Depends(get_units_repo)
) -> UnitService:
    return UnitService(repo)
