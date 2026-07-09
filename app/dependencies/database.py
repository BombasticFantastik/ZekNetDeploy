from fastapi import Depends

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

from app.repositories.photoscan import PhotoScanRepository
from app.services.photoscan import PhotoScanService
from app.services.detection_service import PhotoScanMLService
from app.dependencies.machine_learning import get_ml_service
from app.dependencies.minio import get_minio_client
from app.core.minio_client import MinIOCLient

def get_photoscan_repo(db: AsyncSession = Depends(get_db)):
    return PhotoScanRepository(db)


def get_photoscan_service(
    ml: PhotoScanMLService = Depends(get_ml_service),
    repo: PhotoScanRepository = Depends(get_photoscan_repo),
    minio: MinIOCLient = Depends(get_minio_client),
) -> PhotoScanRepository:
    return PhotoScanService(ml, minio, repo)