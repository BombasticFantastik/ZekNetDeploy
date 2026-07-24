from typing import Annotated
from fastapi import APIRouter, UploadFile, File, Response, Depends

from app.dependencies import get_bucket_loader_service, get_bucket_loader_repo
from app.services import BucketLoaderService
from app.repositories import BucketLoaderRepository

router = APIRouter(
    prefix="/api/v1/bucket_loader",
    tags=["MinIO photo loader"]
)


@router.post("/inference")
async def upload_inference(
    file: Annotated[UploadFile, File(...)],
    service: Annotated[BucketLoaderService, Depends(get_bucket_loader_service)]
):
    content = await file.read()
    return await service.upload_inference(content)


@router.get("/image/{bucket}/{file_id}")
async def get_image(
    bucket: str,
    file_id: str,
    repo: Annotated[BucketLoaderRepository, Depends(get_bucket_loader_repo)]
):
    data = await repo.get_image(bucket, file_id)
    return Response(content=data, media_type="image/jpeg")
