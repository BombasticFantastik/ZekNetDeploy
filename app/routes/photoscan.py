from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from typing import Annotated

from app.dependencies.photoscan import get_photoscan_service
from app.services.photoscan import PhotoScanService

from app.schemas.prisoners import PrisonerUnitPatch, PrisonerGet


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
    try:
        file_bytes = await file.read()

        ml_session = await service.process_formation(
            unit_id=unit_id,
            file_bytes=file_bytes,
            filename=file.filename
        )

        report = await service.build_report(ml_session.id)

        return report

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise


@router.get("/sessions/{ml_session_id}/report")
async def build_report(
    ml_session_id: int, 
    service: Annotated[PhotoScanService, Depends(get_photoscan_service)]
):
    return await service.build_report(ml_session_id)


# Роуты для добавления и изменения людей вынести в отдельный файл
@router.post("/prisoners")
async def add_prisoners(
    files: Annotated[list[UploadFile], File(...)],
    fios: Annotated[list[str] | None, Form()],
    unit_id: Annotated[list[int], Form()],
    service: Annotated[PhotoScanService, Depends(get_photoscan_service)]
):
    """
    Принимает файлы и ФИО. Проверяет дубликаты по имени файла в MinIO/Postgres.
    Грузит новые фото в MinIO, векторизует и сохраняет в БД с ФИО
    """
    return await service.embedding_formation(files, fios, unit_id)


@router.patch("/prisoners/{prisoner_id}", response_model=PrisonerUnitPatch)
async def edit_prisoner(
    prisoner_id: int,
    payload: PrisonerUnitPatch,
    service: Annotated[PhotoScanService, Depends(get_photoscan_service)]
):
    return await service.update_prisoner(
        prisoner_id=prisoner_id,
        user_data=payload
    )


@router.get("/prisoners/{prisoner_id}", response_model=PrisonerGet)
async def get_prisoner(
    prisoner_id: int,
    service: Annotated[PhotoScanService, Depends(get_photoscan_service)]
):
    prisoner = await service.get_prisoner(prisoner_id)

    if not prisoner:
        raise HTTPException(status_code=404, detail="Not found")

    return prisoner


@router.get("/prisoners", response_model=list[PrisonerGet])
async def get_prisoners(
    service: Annotated[PhotoScanService, Depends(get_photoscan_service)],
    unit_id: Annotated[int | None, Query()] = None
):
    return await service.get_prisoners(unit_id)


@router.delete("/prisoners/{prisoner_id}")
async def delete_prisoner(
    prisoner_id: int,
    service: Annotated[PhotoScanService, Depends(get_photoscan_service)]
):
    result = await service.delete_prisoner(prisoner_id)

    if not result:
        raise HTTPException(status_code=404, detail="Not found")

    return {"status": "deleted"}