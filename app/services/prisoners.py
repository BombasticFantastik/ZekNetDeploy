from fastapi import HTTPException

from app.repositories import PrisonerRepository
from app.core.minio_client import MinIOCLient
from app.schemas.prisoners import PrisonerUnitPatch
from app.core.config import settings


class PrisonerService:
    def __init__(
        self,
        repo: PrisonerRepository,
        minio: MinIOCLient
    ):
        self.repo = repo
        self.minio = minio

    async def update_prisoner(self, prisoner_id, user_data: PrisonerUnitPatch):
        data_to_put = user_data.model_dump(exclude_unset=True)

        prisoner = await self.repo.update_prisoner(prisoner_id, data_to_put)

        if not prisoner:
            raise HTTPException(status_code=404, detail="Prisoner not found")

        return prisoner

    async def delete_prisoner(self, prisoner_id: int):
        prisoner = await self.repo.get_prisoner(prisoner_id)

        if not prisoner:
            return False

        await self.minio.delete_image(
            bucket=settings.INFERENCE_BUCKET,
            file_id=prisoner.photo_minio_path
        )

        return await self.repo.delete_prisoner(prisoner_id)

    async def get_prisoner(self, prisoner_id: int):
        return await self.repo.get_prisoner(prisoner_id)

    async def get_prisoners(self, unit_id: int | None = None):
        return await self.repo.get_prisoners(unit_id)
