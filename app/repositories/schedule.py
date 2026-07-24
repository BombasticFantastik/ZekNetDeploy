from datetime import date
from sqlalchemy import select

from app.db_models.prisoner_schedules import PrisonerSchedule

from app.repositories import BaseRepository

class ScheduleRepository(BaseRepository):

    async def create_edit_schedule(
            self, 
            prisoner_id: int, 
            date: date, 
            status: str | None = "PRESENT", 
            note: str | None = None
    ) -> PrisonerSchedule:
        exist = await self.db.scalar(
            select(PrisonerSchedule)
            .where(PrisonerSchedule.prisoner_id == prisoner_id)
            .where(PrisonerSchedule.date == date)
        )

        if exist:
            exist.status = status
            exist.note = note
            await self.db.flush()
            await self.db.commit()
            return exist
        else:
            new_schedule = PrisonerSchedule(
                prisoner_id=prisoner_id,
                date=date,
                status=status,
                note=note
            )
            self.db.add(new_schedule)

        await self.db.flush()
        await self.db.commit()
        return new_schedule

    async def get_schedule_status(
            self, 
            prisoner_id: int, 
            date: date
    ) -> PrisonerSchedule | None:
        return await self.db.scalar(
            select(PrisonerSchedule)
            .where(PrisonerSchedule.prisoner_id == prisoner_id)
            .where(PrisonerSchedule.date == date)
        )

    async def get_schedules(
        self,
        prisoner_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[PrisonerSchedule]:
        query = select(PrisonerSchedule)

        if prisoner_id is not None:
            query = query.where(PrisonerSchedule.prisoner_id == prisoner_id)
        if date_from is not None:
            query = query.where(PrisonerSchedule.date >= date_from)
        if date_to is not None:
            query = query.where(PrisonerSchedule.date <= date_to)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def delete_schedule(self, schedule_id: int) -> bool:
        schedule = await self.db.get(PrisonerSchedule, schedule_id)

        if not schedule:
            return False

        await self.db.delete(schedule)
        await self.db.commit()
        return True