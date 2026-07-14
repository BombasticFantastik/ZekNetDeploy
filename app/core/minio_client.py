import aioboto3
from uuid import uuid4
from io import BytesIO
from contextlib import asynccontextmanager
from types_aiobotocore_s3.client import S3Client

# Два наших бакета в MinIO хранилище
# buildings - фото построений (сырой вход)
# inference - новые фото для обработки и отчётов


class MinIOCLient:
    def __init__(self, endpoint_url, access_key, secret_key, secure, region="us-east-1"):
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.secure = secure
        # Сессия создается один раз и является неявным атрибутом класса, крч не трогать!
        self._session = aioboto3.Session()

    @asynccontextmanager
    async def _get_s3_client(self):
        async with self._session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            use_ssl=self.secure # Защита для сохранности данных
        ) as s3:
            s3_client: S3Client = s3
            yield s3_client
        
    async def put_image(self, bucket: str, data: bytes, content_type="image/jpeg", file_id: str | None = None) -> str:
        if not file_id:
            file_id = f"{uuid4()}.jpg"
        async with self._get_s3_client() as s3:
            await s3.put_object(
                Bucket=bucket,
                Key=file_id,
                Body=data,
                ContentType=content_type,
            )

        return file_id
    
    async def get_image(self, bucket: str, file_id: str) -> bytes:
        async with self._get_s3_client() as s3:
            response = await s3.get_object(Bucket=bucket, Key=file_id)
            return await response["Body"].read()
        
    async def list_images(self, bucket: str) -> list[str]:
        file_keys = []
        async with self._get_s3_client() as s3:
            paginator = s3.get_paginator("list_objects_v2")
            async for page in paginator.paginate(Bucket=bucket):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        file_keys.append(obj["Key"])

        return file_keys