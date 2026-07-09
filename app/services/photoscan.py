from app.core.minio_client import MinIOCLient
from app.services.detection_service import PhotoScanMLService
from app.repositories.photoscan import PhotoScanRepository
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


class PhotoScanService:
    def __init__(
        self, 
        service: PhotoScanMLService, 
        minio: MinIOCLient,
        repo: PhotoScanRepository
    ):
        self.service = service
        self.minio = minio
        self.repo = repo

    async def process_formation(self, file_bytes: bytes, filename: str):
        detected_faces = self.service.process_raw_image_bytes(file_bytes)

        if not detected_faces:
            return {
                "status": "success",
                "message": "Лица не найдены",
                "faces_count": 0,
                "verified_members": []
            }
        
        session = await self.repo.create_session(filename, len(detected_faces))

        report = []

        for face in detected_faces:
            file_id = await self.minio.put_image(
                bucket=settings.BUILDINGS_BUCKET,
                data=face["face_bytes"],
                content_type="image/jpeg"
            )

            cropped_path = f"{settings.BUILDINGS_BUCKET}/{file_id}"

            matched_rows = await self.repo.find_match(face["embedding"])

            await self.repo.create_log(  # Вынести в репо слой (бэкенд)
                session.id,
                matched_rows["id"],
                face["score"],
                face["bbox"],
                cropped_path
            )

            report.append({
                "matched_person_minio_identity": matched_rows["photo"],
                "confidence_score": face["score"],
                "bbox": face["bbox"],
                "cropped_face_storage_path": cropped_path,
                "image_base64": face["image_base64"]
            })

        await self.repo.commit()

        return {
            "status": "success",
            "session_id": session.id,
            "total_detected_faces": len(detected_faces),
            "verified_members": report
        }