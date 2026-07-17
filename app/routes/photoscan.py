from fastapi import APIRouter, Depends, UploadFile, File, Form
from typing import Annotated, List

from app.dependencies.photoscan import get_photoscan_service
from app.services.photoscan import PhotoScanService


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


@router.post("/scan_list")
async def scan_list_formation(
    files: Annotated[list[UploadFile], File(...)],
    fios: Annotated[list[str] | None, Form()],
    unit_id: Annotated[list[int], Form()],
    service: PhotoScanService = Depends(get_photoscan_service)
):
    """
    Принимает файлы и ФИО. Проверяет дубликаты по имени файла в MinIO/Postgres.
    Грузит новые фото в MinIO, векторизует и сохраняет в БД с ФИО
    """
    return await service.embedding_formation(files, fios, unit_id)