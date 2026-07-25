from app.db_models.attendance_sessions import AttendanceSession
from app.db_models.attendance_logs import AttendanceLog
from app.db_models.prisoners_etalons import PrisonerEtalon, Unit

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.repositories.base import BaseRepository


class PhotoScanRepository(BaseRepository):

    async def create_session(
            self,
            unit_id: int,
            snapshot_path: str,
            detected_count: int
    ) -> AttendanceSession:
        session = AttendanceSession(
            unit_id=unit_id,
            snapshot_minio_path=snapshot_path,
            detected_count=detected_count
        )

        self.db.add(session)
        await self.db.flush()
        return session

    async def find_match(self, embedding: list[float]):
        if embedding is None:
            return None

        distance = PrisonerEtalon.face_embedding.cosine_distance(embedding)

        result = await self.db.execute(
            select(
                PrisonerEtalon.id,
                PrisonerEtalon.photo_minio_path,
                PrisonerEtalon.fio,
                distance.label("distance")
            )
            .where(PrisonerEtalon.face_embedding.isnot(None))
            .order_by(distance)
            .limit(1)
        )

        row = result.first()

        if row:
            print(
                "MATCH:",
                row[2],
                "DISTANCE:",
                row[3]
            )
            return {
                    "id": row[0],
                    "photo": row[1],
                    "fio": row[2],
                    "distance": row[3]
            }

        else:
            print("NO ETALONS")
            return None

    async def create_log(
        self,
        session_id: int,
        matched_prisoner_id: int,
        face_detection_score: float,
        bbox: list[int],
        cropped_face_minio_path: str,
        match_distance: float,
        is_verified: bool
    ) -> None:
        log = AttendanceLog(
            session_id=session_id,
            matched_prisoner_id=matched_prisoner_id,
            face_detection_score=face_detection_score,
            bbox=bbox,
            cropped_face_minio_path=cropped_face_minio_path,
            match_distance=match_distance,
            is_verified=is_verified
        )

        self.db.add(log)

    async def get_existing_paths(self, paths: list[str]):
        result = await self.db.scalars(
            select(PrisonerEtalon.photo_minio_path)
            .where(PrisonerEtalon.photo_minio_path.in_(paths))
        )

        return set(result.all())

    async def create_etalon(
        self,
        photo_path: str,
        embedding: list[float],
        unit_id: int,
        fio: str | None = None
    ) -> None:
        etalon = PrisonerEtalon(
            photo_minio_path=photo_path,
            face_embedding=embedding,
            fio=fio,
            unit_id=unit_id
        )

        self.db.add(etalon)

    async def get_session_with_details(self, session_id: int):
        result = await self.db.execute(
            select(AttendanceSession)
            .where(AttendanceSession.id == session_id)
            .options(
                selectinload(AttendanceSession.unit)
                .selectinload(Unit.prisoners),
                selectinload(AttendanceSession.attendance_logs)
                .selectinload(AttendanceLog.matched_prisoner)
            )
        )

        return result.scalar_one_or_none()