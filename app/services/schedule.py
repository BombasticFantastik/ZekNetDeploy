from app.repositories import ScheduleRepository
from datetime import date


class ScheduleService:
    def __init__(self, repo: ScheduleRepository):
        self.repo = repo

    async def create_schedule(
        self,
        prisoner_id: int,
        date_from: date,
        date_to: date,
        status: str | None = "PRESENT",
        note: str | None = None
    ):
        return await self.repo.create_schedule(prisoner_id, date_from, date_to, status, note)

    async def get_schedule(
        self,
        prisoner_id: int,
        target_date: date
    ):
        return await self.repo.get_schedule_status(prisoner_id, target_date)

    async def get_schedules(
        self,
        prisoner_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        return await self.repo.get_schedules(prisoner_id, date_from, date_to)

    async def update_schedule(self, schedule_id: int, data: dict):
        return await self.repo.update_schedule(schedule_id, data)

    async def delete_schedule(self, schedule_id: int):
        return await self.repo.delete_schedule(schedule_id)