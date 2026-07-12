from app.core.minio_client import MinIOCLient
from app.core.config import settings


class BucketLoaderRepository:
    def __init__(self, minio_client: MinIOCLient):
        self.minio = minio_client

    async def upload_face(self, face_bytes: bytes) -> str:
        file_id = await self.minio.put_image(
            bucket=settings.INFERENCE_BUCKET,
            data=face_bytes,
            content_type="image/jpeg"
        )
        return file_id

    async def get_image(self, bucket: str, file_id: str) -> bytes:
        return await self.minio.get_image(bucket, file_id)
