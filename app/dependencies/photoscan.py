from fastapi import Depends

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

from app.repositories.units import UnitRepository
from app.dependencies.units import get_units_repo
from app.repositories.photoscan import PhotoScanRepository
from app.services.photoscan import PhotoScanService
from app.services.detection_service import PhotoScanMLService
from app.dependencies.machine_learning import get_ml_service, get_embedding_service
from app.dependencies.minio import get_minio_client
from app.core.minio_client import MinIOCLient
from app.services.embedding_service import EmbeddingMLService


def get_photoscan_repo(db: AsyncSession = Depends(get_db)):
    return PhotoScanRepository(db)


def get_photoscan_service(
    ml: PhotoScanMLService = Depends(get_ml_service),
    embedding_service: EmbeddingMLService = Depends(get_embedding_service),
    repo: PhotoScanRepository = Depends(get_photoscan_repo),
    minio: MinIOCLient = Depends(get_minio_client),
    u_repo: UnitRepository = Depends(get_units_repo)
) -> PhotoScanService:
    return PhotoScanService(ml, embedding_service, minio, repo, u_repo)