from fastapi import APIRouter, UploadFile, File, Response, Depends

from app.dependencies.bucket_loader import get_bucket_loader_service, get_bucket_loader_repo
from app.services.bucket_loader import BucketLoaderService
from app.repositories.bucket_loader import BucketLoaderRepository

router = APIRouter(
    prefix="/api/v1/bucket_loader",
    tags=["MinIO photo loader"]
)


@router.post("/upload/inference")
async def upload_inference(
    file: UploadFile = File(...),
    service: BucketLoaderService = Depends(get_bucket_loader_service)
):
    content = await file.read()
    result = await service.upload_inference(content)
    return result


@router.get("/image/{bucket}/{file_id}")
async def get_image(
    bucket: str,
    file_id: str,
    repo: BucketLoaderRepository = Depends(get_bucket_loader_repo)
):
    # Возвращаем изображение напрямую
    data = await repo.get_image(bucket, file_id)
    return Response(content=data, media_type="image/jpeg")
