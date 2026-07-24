from fastapi import Depends

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

from app.repositories import UnitRepository, PhotoScanRepository, ScheduleRepository
from app.dependencies.providers.units import get_units_repo
from app.dependencies.providers.schedule import get_schedule_repo
from app.services import PhotoScanService, PhotoScanMLService, EmbeddingMLService
from app.dependencies.providers.machine_learning import get_ml_service, get_embedding_service
from app.dependencies.providers.minio import get_minio_client
from app.core.minio_client import MinIOCLient


def get_photoscan_repo(db: AsyncSession = Depends(get_db)):
    return PhotoScanRepository(db)


def get_photoscan_service(
    ml: PhotoScanMLService = Depends(get_ml_service),
    embedding_service: EmbeddingMLService = Depends(get_embedding_service),
    repo: PhotoScanRepository = Depends(get_photoscan_repo),
    minio: MinIOCLient = Depends(get_minio_client),
    u_repo: UnitRepository = Depends(get_units_repo),
    s_repo: ScheduleRepository = Depends(get_schedule_repo)
) -> PhotoScanService:
    return PhotoScanService(ml, embedding_service, minio, repo, u_repo, s_repo)
