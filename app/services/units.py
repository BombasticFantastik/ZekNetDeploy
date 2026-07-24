from app.db_models.prisoners_etalons import Unit
from app.repositories import UnitRepository

from app.core.config import settings

from fastapi import HTTPException


class UnitService:
    def __init__(self, repo: UnitRepository):
        self.repo = repo

    async def create(self, unit_name: str) -> Unit:
        unit = await self.repo.create_unit(unit_name)

        await self.repo.db.commit()
        return unit
    
    async def get_by_id(self, unit_id: int) -> Unit | None:
        return await self.repo.get_unit_by_id(unit_id)
    
    async def get_all(self) -> list[Unit]:
        return await self.repo.get_all_units()
    
    async def delete(self, unit_id: int) -> bool:
        unit = await self.repo.get_unit_by_id(unit_id)
        if not unit:
            raise HTTPException(status_code=404, detail="Отряд не найден")

        result = await self.repo.delete(unit_id)

        if result:
            await self.repo.db.commit()
            return True
        
        else:
            return False