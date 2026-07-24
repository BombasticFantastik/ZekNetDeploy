from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_units_service
from app.services import UnitService
from app.schemas.unit import UnitCreate


router = APIRouter(
    prefix="/api/v1/units",
    tags=["Units"]
)


@router.post("/", status_code=201)
async def create_unit(
    payload: UnitCreate,
    service: Annotated[UnitService, Depends(get_units_service)]
):
    return await service.create(payload.name)


@router.get("/{unit_id}")
async def get_unit(
    unit_id: int,
    service: Annotated[UnitService, Depends(get_units_service)]
):
    unit = await service.get_by_id(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Отряд не найден")
    return unit


@router.get("/")
async def get_all_units(
    service: Annotated[UnitService, Depends(get_units_service)]
):
    return await service.get_all()


@router.delete("/{unit_id}")
async def delete_unit(
    unit_id: int,
    service: Annotated[UnitService, Depends(get_units_service)]
):
    deleted = await service.delete(unit_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Отряд не найден")
    return {"detail": "Отряд удалён"}