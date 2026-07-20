from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models.attendance_sessions import AttendanceSession
from app.db_models.attendance_logs import AttendanceLog
from app.db_models.prisoners_etalons import PrisonerEtalon, Unit

from sqlalchemy import select
from sqlalchemy.orm import selectinload

class PhotoScanRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, unit_id, snapshot_path, detected_count):
        session = AttendanceSession(
            unit_id=unit_id,
            snapshot_minio_path=snapshot_path,
            detected_count=detected_count
        )

        self.db.add(session)
        await self.db.flush()
        return session
    
    async def find_match(self, embedding):
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
        session_id,
        matched_prisoner_id,
        face_detection_score,
        bbox,
        cropped_face_minio_path,
        match_distance,
        is_verified
    ):
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
    
    def create_etalon(
            self, 
            photo_path: str, 
            embedding: list[float],  
            unit_id: int, 
            fio: str | None = None
    ):
        etalon = PrisonerEtalon(
            photo_minio_path=photo_path,
            face_embedding=embedding,
            fio=fio,
            unit_id=unit_id
        )

        self.db.add(etalon)

    async def commit(self):
        await self.db.commit()

    # Вынести отдельно репозиторий создания отчета
    async def get_session_with_details(self, session_id:int):
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
    
    # Вынести в круд функции для людей
    async def update_prisoner(self, prisoner_id: int, user_data: dict):
        prisoner = await self.db.get(PrisonerEtalon, prisoner_id)

        if not prisoner:
            return None

        if "unit_id" in user_data:
            unit = await self.db.get(Unit, user_data["unit_id"])
            if not unit:
                raise ValueError("Unit not found")

        allowed_fields = {"unit_id", "fio"}

        for key, value in user_data.items():
            if key in allowed_fields:
                setattr(prisoner, key, value)

        await self.db.commit()
        await self.db.refresh(prisoner)

        return prisoner

    
    async def get_prisoner(self, prisoner_id: int):
        prisoner = await self.db.get(PrisonerEtalon, prisoner_id)

        if not prisoner:
            return None
        
        return prisoner
    
    async def get_prisoners(self, unit_id: int | None = None):
        query = select(PrisonerEtalon)

        if unit_id is not None:
            query = query.where(PrisonerEtalon.unit_id == unit_id)

        result = await self.db.scalars(query)
        return result.all()
    
    async def delete_prisoner(self, prisoner_id: int):
        prisoner = await self.db.get(PrisonerEtalon, prisoner_id)

        if not prisoner:
            return False
        
        await self.db.delete(prisoner)
        await self.db.commit()
        return True