from fastapi import APIRouter, UploadFile, File, Response, Depends, HTTPException
import numpy as np
import cv2

from app.core.minio_client import MinIOCLient
from app.dependencies.minio import get_minio_client
from app.core.config import settings

from app.core.cv_engine import detect_faces
from app.core.cv_engine import cv_engine

router = APIRouter(
    prefix="/api/v1/bucket_loader",
    tags=["MinIO photo loader"]
)

# +
@router.post("/upload/inference")
async def upload_inference(
    file: UploadFile = File(...),
    minio: MinIOCLient = Depends(get_minio_client)
):
    """
    Принимает групповое фото, режет его на лица и автоматически 
    загружает каждый кроп в MinIO как отдельный файл-эталон
    """
    content = await file.read()

    nparr = np.frombuffer(content, np.uint8) # FIX
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR) # FIX

    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image file")
    
    detected_faces = detect_faces(
        image=image,
        detector=cv_engine.detector,
        conf_thresh=0.25
    ) # FIX

    uploaded_ids = [] # FIX

    for idx, face in enumerate(detected_faces): # FIX всю часть for
        face_numpy = face["image"]

        success, encoded_image = cv2.imencode(".jpg", face_numpy) # FIX
        if not success:
            print(f"Не удалось закодировать лицо #{idx}")
            continue

        face_bytes = encoded_image.tobytes() # FIX

        try:
            file_id = await minio.put_image(
                bucket=settings.INFERENCE_BUCKET,
                data=face_bytes,
                content_type="image/jpeg"
            ) # FIX
            uploaded_ids.append(file_id) # FIX

        except Exception as e:
            print(f"Ошибка сохранения лица #{idx} в MinIO: {e}")

    return {
        "status": "success",
        "message": f"Эталонов загружено: {len(uploaded_ids)} из {len(detected_faces)}",
        "uplodaed_file_ids": uploaded_ids
    }

# -
@router.get("/image/{bucket}/{file_id}")
def get_image(bucket: str, file_id: str):
    data = MinIOCLient.get_image(bucket, file_id)

    return {
        "file_id": file_id,
        "bucket": bucket,
        "data": Response(content=data, media_type="image/jpeg")
    }