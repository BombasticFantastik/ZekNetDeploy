from app.core.minio_client import MinIOCLient
from app.services.detection_service import PhotoScanMLService
from app.repositories.photoscan import PhotoScanRepository
from app.repositories.units import UnitRepository
from app.services.embedding_service import EmbeddingMLService
from app.schemas.prisoners import PrisonerUnitPatch

from uuid import uuid4
from fastapi import UploadFile, HTTPException

from app.core.config import settings


class PhotoScanService:
    def __init__(
        self, 
        service: PhotoScanMLService, 
        embedding_service: EmbeddingMLService,
        minio: MinIOCLient,
        repo: PhotoScanRepository,
        u_repo: UnitRepository
    ):
        self.service = service
        self.embedding_service = embedding_service
        self.minio = minio
        self.repo = repo
        self.u_repo = u_repo

    async def process_formation(
            self, 
            file_bytes: bytes, 
            filename: str, 
            unit_id: int
    ):
        detected_faces = self.service.process_raw_image_bytes(file_bytes)


        if not detected_faces:
            return {
                "status": "success",
                "message": "Лица не найдены",
                "faces_count": 0,
                "verified_members": []
            }
        
        print("faces:", len(detected_faces))

        for i, face in enumerate(detected_faces):
            print(
                i,
                face["embedding"][:5],
                face["score"]
            )

        unit = await self.u_repo.get_unit_by_id(unit_id)

        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")
        
        session = await self.repo.create_session(
            unit_id,
            filename,
            len(detected_faces)
        )

        report = []

        for face in detected_faces:
            file_id = await self.minio.put_image(
                bucket=settings.BUILDINGS_BUCKET,
                data=face["face_bytes"],
                content_type="image/jpeg"
            )

            cropped_path = file_id

            matched_rows = await self.repo.find_match(face["embedding"])

            match_distance = None
            is_verified = False
            matched_prisoner_id = None
            matched_photo = None
            matched_fio = None
            MATCH_THRESHOLD = 0.6

            if matched_rows:
                match_distance = matched_rows["distance"]

                if match_distance <= MATCH_THRESHOLD:
                    matched_prisoner_id = matched_rows["id"]
                    matched_photo = matched_rows["photo"]
                    matched_fio = matched_rows["fio"]
                    is_verified = True

                else:
                    matched_prisoner_id = None

            await self.repo.create_log(
                session.id,
                matched_prisoner_id,
                face["score"],
                face["bbox"],
                cropped_path,
                match_distance,
                is_verified
            )

            report.append({
                "matched": bool(matched_rows),
                "matched_person_minio_identity": matched_photo,
                "matched_person_fio": matched_fio,
                "match_distance": match_distance,
                "face_detection_score": face["score"],
                "bbox": face["bbox"],
                "cropped_face_storage_path": cropped_path,
                "image_base64": face["image_base64"]
            })

        await self.repo.commit()

        return session
    
    async def embedding_formation(
            self, 
            files: list[UploadFile], 
            fios: list[str], 
            unit_ids: list[int]
    ):
        if not (len(files) == len(fios) == len(unit_ids)):
            raise ValueError("files, fios and unit_ids must have same length")
        
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
        unit_ids_list = unit_ids if unit_ids is not None else []

        for file, fio, unit_id in zip(
            files, 
            fios_list,
            unit_ids_list
        ):
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

            try:
                self.repo.create_etalon(
                    photo_path=unique_filename,
                    embedding=embedding,
                    fio=fio,
                    unit_id=unit_id
                )

                await self.repo.commit()
            except Exception as e:
                await self.minio.delete_image(
                    bucket=settings.INFERENCE_BUCKET,
                    file_id=unique_filename
                )
                raise e

            processed_count += 1

        return {
            "status": "success",
            "newly_vectorized_and_saved": processed_count,
            "skipped_duplicates": skipped_count
        }
    
    async def build_report(self, session_id: int):
        session = await self.repo.get_session_with_details(session_id)

        if not session:
            raise ValueError("Session not found")
        
        exists_prisoners = {p.id for p in session.unit.prisoners}
        
        found_ids = {
            log.matched_prisoner_id: log
            for log in session.attendance_logs
            if log.is_verified and log.matched_prisoner_id in exists_prisoners
        }

        members = []
        unkmembers = []

        for prisoner in session.unit.prisoners:
            log = found_ids.get(prisoner.id)

            if log:
                status = "present"
                members.append({
                    "fio": prisoner.fio,
                    "status": status,
                    "distance": log.match_distance,
                    "etalon_photo": {
                        "bucket": settings.INFERENCE_BUCKET,
                        "path": prisoner.photo_minio_path
                    },
                    "cropped_photo": {
                        "bucket": settings.BUILDINGS_BUCKET,
                        "path": log.cropped_face_minio_path
                    }
                })

            else:
                status = "absent"
                members.append({
                    "fio": prisoner.fio,
                    "status": "absent",
                    "distance": None,
                    "etalon_photo": {
                        "bucket": settings.INFERENCE_BUCKET,
                        "path": prisoner.photo_minio_path
                    },
                    "cropped_photo": None
                })

        for log in session.attendance_logs:
            if log.matched_prisoner_id is None:
                status = "unknown"
                fio = None

                unkmembers.append({
                    "fio": fio,
                    "status": status,
                    "confidence": log.face_detection_score,
                    "distance": None,
                    "etalon_photo": None,
                    "cropped_photo": {
                        "bucket": settings.BUILDINGS_BUCKET,
                        "path": log.cropped_face_minio_path
                    }
                })

        expected_count = len(session.unit.prisoners)
        present_count = len(found_ids)
        absent_count = max((expected_count - present_count), 0)
        unknown_count = len(unkmembers)

        return {
            "session_id": session.id,
            "created_at": session.created_at,

            "unit": {
                "id": session.unit.id,
                "name": session.unit.name
            },

            "summary": {
                "expected": expected_count,
                "present": present_count,
                "absent": absent_count,
                "unknown": unknown_count,
                "detected_total": session.detected_count
            },

            "expected_members": members,
            "unexpected_members": unkmembers
        }

    async def update_prisoner(self, prisoner_id, user_data: PrisonerUnitPatch):
        data_to_put = user_data.model_dump(exclude_unset=True)

        prisoner = await self.repo.update_prisoner(prisoner_id, data_to_put)

        if not prisoner:
            raise HTTPException(status_code=404, detail="Prisoner not found")
        
        return prisoner
    
    async def delete_prisoner(self, prisoner_id: int):
        prisoner = await self.repo.get_prisoner(prisoner_id)

        if not prisoner:
            return False
        
        await self.minio.delete_image(
            bucket=settings.INFERENCE_BUCKET,
            file_id=prisoner.photo_minio_path
        )

        return await self.repo.delete_prisoner(prisoner_id)
    
    async def get_prisoner(self, prisoner_id: int):
        return await self.repo.get_prisoner(prisoner_id)

    async def get_prisoners(self, unit_id: int | None = None):
        return await self.repo.get_prisoners(unit_id)