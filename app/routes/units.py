from fastapi import APIRouter, Depends

from app.dependencies.units import get_units_service
from app.services.units import UnitService
from app.schemas.unit import UnitCreate


router = APIRouter(
    prefix="/api/v1/unit_creator",
    tags=["Units"]
)


@router.post("/")
async def post_unit(
    unit: UnitCreate,
    service: UnitService = Depends(get_units_service)
):
    return await service.create(unit.name)


@router.get("/{unit_id}")
async def get_unit(
    unit_id: int,
    service: UnitService = Depends(get_units_service)
):
    return await service.get_by_id(unit_id)


@router.get("/")
async def get_all_units(
    service: UnitService = Depends(get_units_service)
):
    return await service.get_all()


@router.delete("/{unit_id}")
async def delete_unit(
    unit_id: int,
    service: UnitService = Depends(get_units_service)
):
    return await service.delete(unit_id)