from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Depends
from typing import Annotated

from app.dependencies import get_photoscan_service, get_prisoner_service
from app.services import PhotoScanService, PrisonerService

from app.schemas.prisoners import PrisonerUnitPatch, PrisonerGet


router = APIRouter(
    prefix="/api/v1/photoscan",
    tags=["Photoscan verification"]
)


@router.post("/sessions", status_code=201)
async def create_session(
    file: Annotated[UploadFile, File(...)],
    unit_id: Annotated[int, Form()],
    service: Annotated[PhotoScanService, Depends(get_photoscan_service)]
):
    file_bytes = await file.read()

    ml_session = await service.process_formation(
        unit_id=unit_id,
        file_bytes=file_bytes,
        filename=file.filename
    )

    return await service.build_report(ml_session.id)


@router.get("/sessions/{session_id}/report")
async def get_session_report(
    session_id: int,
    service: Annotated[PhotoScanService, Depends(get_photoscan_service)]
):
    return await service.build_report(session_id)


@router.post("/prisoners", status_code=201)
async def add_prisoners(
    files: Annotated[list[UploadFile], File(...)],
    fios: Annotated[list[str] | None, Form()],
    unit_id: Annotated[list[int], Form()],
    service: Annotated[PhotoScanService, Depends(get_photoscan_service)]
):
    return await service.embedding_formation(files, fios, unit_id)


@router.patch("/prisoners/{prisoner_id}", response_model=PrisonerGet)
async def edit_prisoner(
    prisoner_id: int,
    payload: PrisonerUnitPatch,
    service: Annotated[PrisonerService, Depends(get_prisoner_service)]
):
    return await service.update_prisoner(
        prisoner_id=prisoner_id,
        user_data=payload
    )


@router.get("/prisoners/{prisoner_id}", response_model=PrisonerGet)
async def get_prisoner(
    prisoner_id: int,
    service: Annotated[PrisonerService, Depends(get_prisoner_service)]
):
    prisoner = await service.get_prisoner(prisoner_id)

    if not prisoner:
        raise HTTPException(status_code=404, detail="Заключённый не найден")

    return prisoner


@router.get("/prisoners", response_model=list[PrisonerGet])
async def get_prisoners(
    service: Annotated[PrisonerService, Depends(get_prisoner_service)],
    unit_id: Annotated[int | None, Query()] = None
):
    return await service.get_prisoners(unit_id)


@router.delete("/prisoners/{prisoner_id}")
async def delete_prisoner(
    prisoner_id: int,
    service: Annotated[PrisonerService, Depends(get_prisoner_service)]
):
    result = await service.delete_prisoner(prisoner_id)

    if not result:
        raise HTTPException(status_code=404, detail="Заключённый не найден")

    return {"detail": "Заключённый удалён"}