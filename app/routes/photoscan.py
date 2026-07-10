from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.database import get_photoscan_service
from app.services.photoscan import PhotoScanService
from app.services.detection_service import PhotoScanMLService
from app.repositories.photoscan import PhotoScanRepository
from app.core.minio_client import MinIOCLient


router = APIRouter(
    prefix="/api/v1/photoscan",
    tags=["Photoscan verification"]
)


@router.post("/save_&_scan_&_compare")
async def scan_formation(
    file: UploadFile = File(...),
    service: PhotoScanService = Depends(get_photoscan_service)
):
    """
    Принимает общее фото взвода
    1. Нарезает лица первой моделью
    2. Сохраняет каждое вырезанное лицо (кроп) в MinIO (бакет buildings)
    3. Превращает кроп во временный вектор второй моделью
    4. Сравнивает его через pgvector со всеми эталонами из Postgres
    5. Записывает сессию и логи детекции в базу данных
    """
    file_bytes = await file.read()
    
    result = await service.process_formation(
        file_bytes=file_bytes,
        filename=file.filename
    )

    return result


@router.post("/scan")
async def scan_formation(
    service: PhotoScanService = Depends(get_photoscan_service)
):
    """
    Сканирует бакет эталонов MinIO, находит новые фото, 
    которых еще нет в PostgreSQL, генерирует по ним 512-мерные 
    векторы и сохраняет в базу. Повторно старые фото не обрабатывает
    """
    return await service.embedding_formation()