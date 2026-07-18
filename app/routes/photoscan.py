from fastapi import APIRouter, Depends, UploadFile, File, Form
from typing import Annotated, List

from app.dependencies.photoscan import get_photoscan_service
from app.services.photoscan import PhotoScanService


router = APIRouter(
    prefix="/api/v1/photoscan",
    tags=["Photoscan verification"]
)


@router.post("/scan_save_report")
async def scan_formation(
    file: Annotated[UploadFile, File(...)],
    unit_id: Annotated[int, Form()],
    service: Annotated[PhotoScanService, Depends(get_photoscan_service)]
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
    
    ml_session = await service.process_formation(
        unit_id=unit_id,
        file_bytes=file_bytes,
        filename=file.filename
    )

    report = await service.build_report(ml_session.id)

    return report


@router.get("/report")
async def build_report(
    ml_session_id: int, 
    service: Annotated[PhotoScanService, Depends(get_photoscan_service)]
):
    return await service.build_report(ml_session_id)


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