from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import numpy as np
import cv2
import faiss

from app.core.cv_engine import cv_engine
from app.utils.vectorization import compare_new_face, open_numpy_as_tensor, get_vector_from_face

from app.core.minio_client import MinIOCLient
from app.dependencies.minio import get_minio_client 
from app.core.config import settings

from app.db_models.attendance_logs import AttendanceLog
from app.db_models.attendance_sessions import AttendanceSession
from app.db_models.prisoners_etalons import PrisonerEtalon
from app.core.database import get_db


router = APIRouter(
    prefix="/api/v1/photoscan",
    tags=["Photoscan verification"]
)


MOCK_ETALON_VECTORS = np.random.randn(5, 512).astype('float32')


def read_image(file: UploadFile):
    contents = file.file.read()
    np_arr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return image

# +
@router.post("/save_&_scan_&_compare")
async def scan_formation(
    file: UploadFile = File(...),
    minio: MinIOCLient = Depends(get_minio_client),
    db: AsyncSession = Depends(get_db)
):
    """
    Принимает общее фото взвода
    1. Нарезает лица первой моделью
    2. Сохраняет каждое вырезанное лицо (кроп) в MinIO (бакет buildings)
    3. Превращает кроп во временный вектор второй моделью
    4. Сравнивает его через pgvector со всеми эталонами из Postgres
    5. Записывает сессию и логи детекции в базу данных
    """
    content = await file.read()

    nparr = np.frombuffer(content, np.uint8) # FIX
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR) # FIX

    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image file")
    
    detected_faces = cv_engine.process_formation_image(image) # FIX

    if not detected_faces:
        return {
            "status": "success",
            "message": "На фотографии построения не обнаружено ни одного лица.",
            "faces_count": 0,
            "present_members": []
        }
    
    new_session = AttendanceSession(
        snapshot_minio_path=file.filename,
        detected_count=len(detected_faces) 
    ) # Вынести в репо слой (бэкенд)
    db.add(new_session) # Вынести в репо слой (бэкенд)
    await db.flush() # Вынести в репо слой (бэкенд)

    final_report = []

    for face in detected_faces:
        x1, y1, x2, y2 = face["bbox"] # FIX
        face_numpy = image[y1:y2, x1:x2] # FIX
        
        if face_numpy.size == 0:
            continue
       
        success, encoded_face = cv2.imencode(".jpg", face_numpy) # FIX
        if not success:
            continue
        face_bytes = encoded_face.tobytes() # FIX

        try:
            cropped_file_id = await minio.put_image(
                bucket=settings.BUILDINGS_BUCKET,
                data=face_bytes,
                content_type="image/jpeg"
            ) # Вынести в репо слой (бэкенд)
            cropped_path = f"{settings.BUILDINGS_BUCKET}/{cropped_file_id}" # Вынести в сервис слой (бэкенд)
        except  Exception as e:
            print(f"Ошибка сохранения кропа в MinIO: {e}")
            cropped_path = "error_saved"

        face_vector = face["embedding"] 

        matched_row = (await db.execute(
            select(PrisonerEtalon.id, PrisonerEtalon.photo_minio_path)
            .order_by(PrisonerEtalon.face_embedding.l2_distance(face_vector))
            .limit(1)
        )).first() # Вынести в репо слой (бэкенд)

        if matched_row:  # Вынести в сервис слой (бэкенд) возможно?
            matched_prisoner_id = matched_row[0]
            prisoner_identity = matched_row[1]
        else: 
            matched_prisoner_id = None
            prisoner_identity = "Unknown object"

        new_log = AttendanceLog(  # Вынести в репо слой (бэкенд)
            session_id=new_session.id,
            matched_prisoner_id=matched_prisoner_id,
            confidence=face["score"],
            bbox=face["bbox"],
            cropped_face_minio_path=cropped_path
        )
        db.add(new_log)  # Вынести в репо слой (бэкенд)

        final_report.append({
            "matched_person_minio_identity": prisoner_identity,
            "confidence_score": face["score"],
            "bbox": face["bbox"],
            "cropped_face_storage_path": cropped_path,
            "image_base64": face["image"]
        })

    await db.commit()  # Вынести в репо слой (бэкенд)

    return {
        "status": "success",
        "session_id": new_session.id,
        "total_detected_faces": len(detected_faces),
        "verified_members": final_report
    }

# +
@router.post("/scan")
async def scan_formation(
    minio: MinIOCLient = Depends(get_minio_client),
    db: AsyncSession = Depends(get_db)
):
    """
    Сканирует бакет эталонов MinIO, находит новые фото, 
    которых еще нет в PostgreSQL, генерирует по ним 512-мерные 
    векторы и сохраняет в базу. Повторно старые фото не обрабатывает
    """
    try:
        minio_files = await minio.list_images(bucket=settings.INFERENCE_BUCKET)  # Вынести в репо слой (бэкенд)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка чтения хранилища MinIO: {e}")
    
    if not minio_files:  # Вынести в репо слой (бэкенд)
        return {
            "status": "success",
            "message": "Бакет эталонов в MinIO пуст"
        }

    existing_paths = set( # Вынести в репо слой (бэкенд)
        (await db.scalars(
            select(PrisonerEtalon.photo_minio_path)
            .where(PrisonerEtalon.photo_minio_path.in_(minio_files))
        )).all()
    )

    new_files = [f for f in minio_files if f not in existing_paths] # Вынести в сервис слой (бэкенд)

    if not new_files:
        return {
            "status": "success",
            "message": "Синхронизация не требуется. Для всех файлов в MinIO уже созданы векторы в БД",
            "total_files_checked": len(minio_files)
        }
    
    new_records_count = 0

    for file_key in new_files:
        try:
            file_bytes = await minio.get_image(  # Вынести в репо слой (бэкенд)
                bucket=settings.INFERENCE_BUCKET,
                file_id=file_key
            )

            nparr = np.frombuffer(file_bytes, np.uint8) # FIX
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR) # FIX

            if image is None:
                print(f"Файл {file_key} поврежден или не является корректным изображением.")
                continue

            face_tensor = open_numpy_as_tensor(image) # FIX
            face_vector = get_vector_from_face(face_tensor, cv_engine.embedder) # FIX
            face_embedding = face_vector.flatten().tolist() # FIX

            new_etalon = PrisonerEtalon(
                photo_minio_path=file_key,
                face_embedding=face_embedding
            ) # Вынести в репо слой (бэкенд)

            db.add(new_etalon) # Вынести в репо слой (бэкенд)
            new_records_count += 1 # Вынести в сервис слой (бэкенд)

        except Exception as e:
            print(f"Не удалось обработать файл {file_key}: {e}")
            continue

    if new_records_count > 0:
        await db.commit() # Вынести в репо слой (бэкенд)

    return {
        "status": "success",
        "total_files_in_minio": len(minio_files),
        "already_processed_earlier": len(existing_paths),
        "newly_vectorized_and_saved": new_records_count
    }