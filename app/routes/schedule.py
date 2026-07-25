from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import date

from app.services import ScheduleService
from app.schemas import SchedulePostSchema, SchedulePatchSchema
from app.dependencies import get_schedule_service


router = APIRouter(
    prefix="/api/v1/schedule",
    tags=["Schedule date editor"]
)


@router.post("/", status_code=201)
async def create_schedule(
    payload: SchedulePostSchema,
    service: Annotated[ScheduleService, Depends(get_schedule_service)]
):
    return await service.create_schedule(
        payload.prisoner_id, payload.date_from, payload.date_to,
        payload.status, payload.note
    )


@router.get("/")
async def get_schedule(
    prisoner_id: int,
    service: Annotated[ScheduleService, Depends(get_schedule_service)],
    target_date: Optional[date] = Query(None, description="YYYY-MM-DD")
):
    if target_date:
        result = await service.get_schedule(prisoner_id, target_date)
        if not result:
            raise HTTPException(status_code=404, detail="Запись не найдена")
        return result
    return await service.get_schedules(prisoner_id=prisoner_id)


@router.get("/list")
async def get_schedules_list(
    service: Annotated[ScheduleService, Depends(get_schedule_service)],
    prisoner_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[date] = Query(None, description="YYYY-MM-DD"),
):
    return await service.get_schedules(
        prisoner_id=prisoner_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.patch("/{schedule_id}")
async def update_schedule(
    schedule_id: int,
    payload: SchedulePatchSchema,
    service: Annotated[ScheduleService, Depends(get_schedule_service)]
):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="Нет полей для обновления")
    result = await service.update_schedule(schedule_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return result


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    service: Annotated[ScheduleService, Depends(get_schedule_service)]
):
    deleted = await service.delete_schedule(schedule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return {"detail": "Запись удалена"}