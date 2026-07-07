from functools import lru_cache

from app.core.minio_client import MinIOCLient
from app.core.config import settings


@lru_cache()
def get_minio_client() -> MinIOCLient:
    return MinIOCLient(
        endpoint_url=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE
    )