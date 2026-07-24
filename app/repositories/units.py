from app.db_models.prisoners_etalons import Unit

from sqlalchemy import select

from app.repositories import BaseRepository

class UnitRepository(BaseRepository):

    async def create_unit(self, unit_name: str) -> Unit:
        new_unit = Unit(
            name=unit_name
        )
        self.db.add(new_unit)
        await self.db.flush()

        return new_unit
    
    async def get_unit_by_id(self, unit_id: int) -> Unit | None:
        result = await self.db.scalar(select(Unit).where(Unit.id == unit_id))
        return result
    
    async def get_all_units(self) -> list[Unit]:
        result = await self.db.scalars(select(Unit))
        return result.all()
    
    async def delete(self, unit_id: int):
        unit = await self.db.get(Unit, unit_id)

        if not unit:
            return False
        
        await self.db.delete(unit)
        return True
