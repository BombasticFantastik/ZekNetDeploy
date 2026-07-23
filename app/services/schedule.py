from app.repositories import ScheduleRepository
from datetime import date


class ScheduleService:
    def __init__(self, repo: ScheduleRepository):
        self.repo = repo

    async def add_upd_schedule(
        self,
        prisoner_id: int,
        date: date,
        status: str | None = "PRESENT",
        note: str | None = None
    ):
        return await self.repo.create_edit_schedule(prisoner_id, date, status, note)

    async def get_schedule(
        self,
        prisoner_id: int,
        date: date
    ):
        return await self.repo.get_schedule_status(prisoner_id, date)

    async def get_schedules(
        self,
        prisoner_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        return await self.repo.get_schedules(prisoner_id, date_from, date_to)

    async def delete_schedule(self, schedule_id: int):
        return await self.repo.delete_schedule(schedule_id)    