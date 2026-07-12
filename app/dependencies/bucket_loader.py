from fastapi import Depends

from app.core.minio_client import MinIOCLient
from app.dependencies.minio import get_minio_client
from app.repositories.bucket_loader import BucketLoaderRepository
from app.services.bucket_loader import BucketLoaderService
from app.core.cv_engine import cv_engine


def get_bucket_loader_repo(
    minio: MinIOCLient = Depends(get_minio_client)
) -> BucketLoaderRepository:
    return BucketLoaderRepository(minio)


def get_bucket_loader_service(
    repo: BucketLoaderRepository = Depends(get_bucket_loader_repo)
) -> BucketLoaderService:
    return BucketLoaderService(detector=cv_engine.detector, repo=repo)
