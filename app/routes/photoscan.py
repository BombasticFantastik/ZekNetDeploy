from datetime import date
from fastapi import APIRouter, UploadFile, File, Form, Query, Depends
from typing import Annotated

from app.dependencies import get_photoscan_service
from app.services import PhotoScanService


router = APIRouter(
    prefix="/api/v1/photoscan",
    tags=["Photoscan verification"]
)


@router.get("/sessions")
async def list_sessions(
    service: Annotated[PhotoScanService, Depends(get_photoscan_service)],
    date: Annotated[date | None, Query()] = None
):
    return await service.list_sessions(date)


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