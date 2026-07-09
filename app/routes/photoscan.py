from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.database import get_photoscan_service
from app.services.photoscan import PhotoScanService
from app.services.detection_service import PhotoScanMLService
from app.repositories.photoscan import PhotoScanRepository
from app.core.minio_client import MinIOCLient


router = APIRouter(
    prefix="/api/v1/photoscan",
    tags=["Photoscan verification"]
)


@router.post("/save_&_scan_&_compare")
async def scan_formation(
    file: UploadFile = File(...),
    service: PhotoScanService = Depends(get_photoscan_service)
):
    """
    Принимает общее фото взвода
    1. Нарезает лица первой моделью
    2. Сохраняет каждое вырезанное лицо (кроп) в MinIO (бакет buildings)
    3. Превращает кроп во временный вектор второй моделью
    4. Сравнивает его через pgvector со всеми эталонами из Postgres
    5. Записывает сессию и логи детекции в базу данных
    """
    file_bytes = await file.read()
    
    result = await service.process_formation(
        file_bytes=file_bytes,
        filename=file.filename
    )

    return result

# # +
# @router.post("/scan")
# async def scan_formation(
#     minio: MinIOCLient = Depends(get_minio_client),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Сканирует бакет эталонов MinIO, находит новые фото, 
#     которых еще нет в PostgreSQL, генерирует по ним 512-мерные 
#     векторы и сохраняет в базу. Повторно старые фото не обрабатывает
#     """
#     try:
#         minio_files = await minio.list_images(bucket=settings.INFERENCE_BUCKET)  # Вынести в репо слой (бэкенд)

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Ошибка чтения хранилища MinIO: {e}")
    
#     if not minio_files:  # Вынести в репо слой (бэкенд)
#         return {
#             "status": "success",
#             "message": "Бакет эталонов в MinIO пуст"
#         }

#     existing_paths = set( # Вынести в репо слой (бэкенд)
#         (await db.scalars(
#             select(PrisonerEtalon.photo_minio_path)
#             .where(PrisonerEtalon.photo_minio_path.in_(minio_files))
#         )).all()
#     )

#     new_files = [f for f in minio_files if f not in existing_paths] # Вынести в сервис слой (бэкенд)

#     if not new_files:
#         return {
#             "status": "success",
#             "message": "Синхронизация не требуется. Для всех файлов в MinIO уже созданы векторы в БД",
#             "total_files_checked": len(minio_files)
#         }
    
#     new_records_count = 0

#     for file_key in new_files:
#         try:
#             file_bytes = await minio.get_image(  # Вынести в репо слой (бэкенд)
#                 bucket=settings.INFERENCE_BUCKET,
#                 file_id=file_key
#             )

#             nparr = np.frombuffer(file_bytes, np.uint8) # FIX
#             image = cv2.imdecode(nparr, cv2.IMREAD_COLOR) # FIX

#             if image is None:
#                 print(f"Файл {file_key} поврежден или не является корректным изображением.")
#                 continue

#             face_tensor = open_numpy_as_tensor(image) # FIX
#             face_vector = get_vector_from_face(face_tensor, cv_engine.embedder) # FIX
#             face_embedding = face_vector.flatten().tolist() # FIX

#             new_etalon = PrisonerEtalon(
#                 photo_minio_path=file_key,
#                 face_embedding=face_embedding
#             ) # Вынести в репо слой (бэкенд)

#             db.add(new_etalon) # Вынести в репо слой (бэкенд)
#             new_records_count += 1 # Вынести в сервис слой (бэкенд)

#         except Exception as e:
#             print(f"Не удалось обработать файл {file_key}: {e}")
#             continue

#     if new_records_count > 0:
#         await db.commit() # Вынести в репо слой (бэкенд)

#     return {
#         "status": "success",
#         "total_files_in_minio": len(minio_files),
#         "already_processed_earlier": len(existing_paths),
#         "newly_vectorized_and_saved": new_records_count
#     }