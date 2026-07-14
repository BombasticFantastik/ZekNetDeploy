from app.core.minio_client import MinIOCLient
from app.services.detection_service import PhotoScanMLService
from app.repositories.photoscan import PhotoScanRepository
from app.services.embedding_service import EmbeddingMLService

from uuid import uuid4
import itertools
from fastapi import UploadFile

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

            await self.repo.create_log(
                session.id,
                matched_rows["id"],
                face["score"],
                face["bbox"],
                cropped_path
            )

            report.append({
                "matched_person_minio_identity": matched_rows["photo"],
                "matched_person_fio": matched_rows["fio"],
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
    
    async def embedding_formation(self, files: list[UploadFile], fios: list[str]):
        DUPLICATE_THRESHOLD = 0.6

        processed_count = 0
        skipped_count = 0

        if not files:
            return {
                "status": "success",
                "newly_vectorized_and_saved": 0,
                "skipped_duplicates": 0
            }
        
        fios_list = fios if fios is not None else []

        for file, fio in itertools.zip_longest(files, fios_list, fillvalue=None):
            if file is None or not file.filename:
                continue

            file_bytes = await file.read()

            embedding = self.embedding_service.create_embedding(file_bytes)

            if not embedding:
                continue

            match = await self.repo.find_match(embedding)

            if match and match["distance"] <= DUPLICATE_THRESHOLD:
                skipped_count += 1
                continue

            ext = (
                file.filename.split(".")[-1]
                if "." in file.filename
                else "jpg"
            )

            unique_filename = f"{uuid4()}.{ext}"

            await self.minio.put_image(
                bucket=settings.INFERENCE_BUCKET,
                file_id=unique_filename,
                data=file_bytes
            )

            self.repo.create_etalon(
                photo_path=unique_filename,
                embedding=embedding,
                fio=fio
            )

            processed_count += 1

        if processed_count:
            await self.repo.commit()

        return {
            "status": "success",
            "newly_vectorized_and_saved": processed_count,
            "skipped_duplicates": skipped_count
        }