from app.core.minio_client import MinIOCLient
from app.services.detection_service import PhotoScanMLService
from app.repositories.photoscan import PhotoScanRepository
from app.services.embedding_service import EmbeddingMLService

from app.core.config import settings


class PhotoScanService:
    def __init__(
        self, 
        service: PhotoScanMLService, 
        embedding_service: EmbeddingMLService,
        minio: MinIOCLient,
        repo: PhotoScanRepository
    ):
        self.service = service
        self.embedding_service = embedding_service
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
    
    async def embedding_formation(self):
        minio_files = await self.minio.list_images(bucket=settings.INFERENCE_BUCKET)
        existing = await self.repo.get_existing_paths(minio_files)

        new_files = [file for file in minio_files if file not in existing]

        for file in new_files:
            file_bytes = await self.minio.get_image(
                bucket=settings.INFERENCE_BUCKET,
                file_id=file
            )

            embedding = self.embedding_service.create_embedding(file_bytes)

            self.repo.create_etalon(
                file,
                embedding
            )

        await self.repo.commit()

        return {
            "status": "success",
            "total_files_in_minio": len(minio_files),
            "already_processed_earlier": len(existing),
            "newly_vectorized_and_saved": len(new_files)
        }