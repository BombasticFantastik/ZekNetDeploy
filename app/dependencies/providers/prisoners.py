from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories import PrisonerRepository
from app.services import PrisonerService
from app.dependencies.providers.minio import get_minio_client
from app.core.minio_client import MinIOCLient


def get_prisoner_repo(db: AsyncSession = Depends(get_db)) -> PrisonerRepository:
    return PrisonerRepository(db)


def get_prisoner_service(
    repo: PrisonerRepository = Depends(get_prisoner_repo),
    minio: MinIOCLient = Depends(get_minio_client),
) -> PrisonerService:
    return PrisonerService(repo, minio)
