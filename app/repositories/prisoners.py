from sqlalchemy import select
from fastapi import HTTPException

from app.db_models.prisoners_etalons import PrisonerEtalon, Unit
from app.repositories.base import BaseRepository


class PrisonerRepository(BaseRepository):

    async def update_prisoner(
        self,
        prisoner_id: int,
        user_data: dict
    ) -> PrisonerEtalon | None:
        prisoner = await self.db.get(PrisonerEtalon, prisoner_id)

        if not prisoner:
            return None

        if "unit_id" in user_data:
            unit = await self.db.get(Unit, user_data["unit_id"])
            if not unit:
                raise HTTPException(status_code=404, detail="Отряд не найден")

        allowed_fields = {"unit_id", "fio"}

        for key, value in user_data.items():
            if key in allowed_fields:
                setattr(prisoner, key, value)

        await self.db.commit()
        await self.db.refresh(prisoner)

        return prisoner

    async def get_prisoner(self, prisoner_id: int) -> PrisonerEtalon | None:
        prisoner = await self.db.get(PrisonerEtalon, prisoner_id)

        if not prisoner:
            return None

        return prisoner

    async def get_prisoners(
        self,
        unit_id: int | None = None
    ) -> list[PrisonerEtalon]:
        query = select(PrisonerEtalon)

        if unit_id is not None:
            query = query.where(PrisonerEtalon.unit_id == unit_id)

        result = await self.db.scalars(query)
        return result.all()

    async def delete_prisoner(self, prisoner_id: int):
        prisoner = await self.db.get(PrisonerEtalon, prisoner_id)

        if not prisoner:
            return False

        await self.db.delete(prisoner)
        await self.db.commit()
        return True
