from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models.attendance_sessions import AttendanceSession
from app.db_models.attendance_logs import AttendanceLog
from app.db_models.prisoners_etalons import PrisonerEtalon

from sqlalchemy import select

class PhotoScanRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, snapshot_path, detected_count):
        session = AttendanceSession(
            snapshot_minio_path=snapshot_path,
            detected_count=detected_count
        )

        self.db.add(session)
        await self.db.flush()
        return session
    
    async def find_match(self, embedding):
        result = await self.db.execute(
            select(
                PrisonerEtalon.id,
                PrisonerEtalon.photo_minio_path,
                PrisonerEtalon.fio
            )
            .order_by(
                PrisonerEtalon.face_embedding.l2_distance(embedding)
            )
            .limit(1)
        )

        row = result.first()

        if row:
            return {
                    "id": row[0],
                    "photo": row[1],
                    "fio": row[2]
            }

        return {
            "id": None,
            "photo": None,
            "fio": None
        }
    
    async def create_log(
        self,
        session_id,
        matched_prisoner_id,
        confidence,
        bbox,
        cropped_face_minio_path
    ):
        log = AttendanceLog(
            session_id=session_id,
            matched_prisoner_id=matched_prisoner_id,
            confidence=confidence,
            bbox=bbox,
            cropped_face_minio_path=cropped_face_minio_path
        )

        self.db.add(log)

    async def get_existing_paths(self, paths: list[str]):
        result = await self.db.scalars(
            select(PrisonerEtalon.photo_minio_path)
            .where(PrisonerEtalon.photo_minio_path.in_(paths))
        )

        return set(result.all())
    
    def create_etalon(self, photo_path: str, embedding: list[float], fio: str | None = None):
        etalon = PrisonerEtalon(
            photo_minio_path=photo_path,
            face_embedding=embedding,
            fio=fio
        )

        self.db.add(etalon)

    async def commit(self):
        await self.db.commit()