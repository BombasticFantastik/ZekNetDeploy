import os
import cv2
import numpy as np
import base64

from app.core.config import settings
# Импортируем твой новый класс детектора из нового места
from app.services.detection_service import SCRFDFaceDetector
# Эмбеддинг и утилиты соседа оставляем нетронутыми
from app.utils.vectorization import BuffaloModel, open_numpy_as_tensor, get_vector_from_face

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

def encode(img):
    _, buffer = cv2.imencode(".jpg", img)
    return base64.b64encode(buffer).decode("utf-8")


class CVEngine:
    def __init__(self):
        self.detector_path = os.path.join(
            BASE_DIR,
            "utils/models_weights/scrfd_500m_bnkps.onnx"
        )
        self.embedder_path = os.path.join(
            BASE_DIR,
            "utils/models_weights/w600k_r50.onnx"
        )

        # ИСПРАВЛЕНО: Теперь инициализируем твой класс детектора вместо старой функции init_detector
        self.detector = SCRFDFaceDetector(model_path=self.detector_path, target_size=2048)
        self.embedder = BuffaloModel(path=self.embedder_path, use_gpu=False)

    def process_formation_image(self, image: np.ndarray) -> list[dict]:
        detected_faces = self.detector.detect_faces(image=image, conf_thresh=0.25)

        faces = []
        for face in detected_faces:
            face_numpy = face["image"]
            
            # ВОЗВРАЩАЕМ КАК БЫЛО: используем строго ту же функцию, что и в /scan!
            face_tensor = open_numpy_as_tensor(face_numpy)
            
            # Передаем тензор, в котором пиксели нормализованы к 0-1
            face_vector = get_vector_from_face(face_tensor, self.embedder)
            clean_vector = face_vector.flatten().tolist()

            faces.append({
                "image": encode(face["image"]),
                "bbox": list(map(int, face["bbox"])),
                "score": float(face["score"]),
                "embedding": clean_vector
            })

        return faces
    

cv_engine = CVEngine()