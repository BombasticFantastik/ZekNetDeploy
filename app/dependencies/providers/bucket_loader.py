from fastapi import Depends

from app.core.minio_client import MinIOCLient
from app.dependencies.providers.minio import get_minio_client
from app.repositories import BucketLoaderRepository
from app.services import BucketLoaderService
from app.core.cv_engine import CVEngine, get_cv_engine


def get_bucket_loader_repo(
    minio: MinIOCLient = Depends(get_minio_client)
) -> BucketLoaderRepository:
    return BucketLoaderRepository(minio)


def get_bucket_loader_service(
    repo: BucketLoaderRepository = Depends(get_bucket_loader_repo),
    engine: CVEngine = Depends(get_cv_engine)
) -> BucketLoaderService:
    return BucketLoaderService(detector=engine.detector, repo=repo)
