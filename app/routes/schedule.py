from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import date

from app.services import ScheduleService
from app.schemas import SchedulePostPutSchema
from app.dependencies import get_schedule_service


router = APIRouter(
    prefix="/api/v1/schedule",
    tags=["Schedule date editor"]
)


@router.put("/")
async def create_edit_schedule(
    payload: SchedulePostPutSchema,
    service: Annotated[ScheduleService, Depends(get_schedule_service)]
):
    return await service.add_upd_schedule(
        payload.prisoner_id, payload.date, payload.status, payload.note
    )


@router.get("/")
async def get_schedule(
    prisoner_id: int,
    service: Annotated[ScheduleService, Depends(get_schedule_service)],
    date: Optional[date] = Query(None, description="YYYY-MM-DD")
):
    if date:
        result = await service.get_schedule(prisoner_id, date)
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


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    service: Annotated[ScheduleService, Depends(get_schedule_service)]
):
    deleted = await service.delete_schedule(schedule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return {"detail": "Запись удалена"}