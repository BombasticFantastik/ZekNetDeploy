import numpy as np
import cv2
from fastapi import HTTPException

from app.repositories import BucketLoaderRepository


class BucketLoaderService:
    def __init__(self, detector, repo: BucketLoaderRepository):
        self.detector = detector
        self.repo = repo

    async def upload_inference(
        self, image_bytes: bytes, conf_thresh: float = 0.25
    ) -> dict:
        # Декодируем изображение
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image file")

        # Детектируем лица
        detected_faces = self.detector.detect_faces(
            image=image, conf_thresh=conf_thresh
        )

        uploaded_ids = []
        for idx, face in enumerate(detected_faces):
            face_numpy = face["image"]

            # Кодируем в JPEG
            success, encoded = cv2.imencode(".jpg", face_numpy)
            if not success:
                # Лог ошибки через принт - надо исправить
                print(f"Не удалось закодировать лицо #{idx}")
                continue

            face_bytes = encoded.tobytes()

            try:
                file_id = await self.repo.upload_face(face_bytes)
                uploaded_ids.append(file_id)
            except Exception as e:
                print(f"Ошибка сохранения лица #{idx} в MinIO: {e}")

        return {
            "status": "success",
            "message": (
                f"Эталонов загружено: {len(uploaded_ids)} "
                f"из {len(detected_faces)}"
            ),
            "uploaded_file_ids": uploaded_ids
        }
