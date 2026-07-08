import base64
from typing import TypedDict, List
import cv2
import numpy as np
import os
import torch

# Твои импорты интерфейсов и детектора
from app.interfaces.image_processing import FaceDetectorInterface
from app.utils.image_processing import SCRFDFaceDetector

# Импорты эмбеддера напарника
from app.utils.vectorization import BuffaloModel, open_numpy_as_tensor, get_vector_from_face

class ProcessedFaceResult(TypedDict):
    image_base64: str          # Закодированное в base64 изображение (для фронта)
    face_bytes: bytes          # Сжатые байты .jpg для сохранения в MinIO
    bbox: list[int]            # Координаты лица
    score: float               # Уверенность модели
    embedding: list[float]     # РЕАЛЬНЫЙ вектор для pgvector


class PhotoScanMLService:
    def __init__(self, detector: FaceDetectorInterface, embedder: BuffaloModel):
        self.detector = detector
        self.embedder = embedder

    def process_raw_image_bytes(self, content: bytes) -> list[ProcessedFaceResult]:
        """
        Берет сырые байты общего фото, находит лица через детектор 
        и векторизует их строго через face["image"].
        """
        nparr = np.frombuffer(content, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return []

        # Детектор сам бережно вырежет лица с учетом BORDER и запишет в face["image"]
        detected_faces = self.detector.detect_faces(image)
        final_ml_results: list[ProcessedFaceResult] = []
        
        for face in detected_faces:
            # Берем ГОТОВЫЙ кроп лица из детектора. Руками по bbox из image больше не режем!
            face_numpy = face["image"]
            
            if face_numpy.size == 0:
                continue
                
            # 1. Сжимаем матрицу лица в JPG-байты для MinIO
            success, encoded_face = cv2.imencode(".jpg", face_numpy)
            if not success:
                continue
            face_bytes = encoded_face.tobytes()
            
            # 2. Делаем base64 строку для фронтенда
            image_base64 = base64.b64encode(face_bytes).decode("utf-8")
            
            # 3. Работа с эмбеддером в точности как в старом cv_engine
            try:
                # Превращаем готовый кроп в тензор [1, 3, 112, 112] через функцию напарника
                tensor_img = open_numpy_as_tensor(face_numpy)
                
                # Извлекаем эмбеддинг
                vector_np = get_vector_from_face(tensor_img, self.embedder)
                
                # Сглаживаем в плоский список для базы данных
                clean_vector = vector_np.flatten().tolist()
            except Exception as e:
                # КРИТИЧНО: раньше при ошибке clean_vector не переопределялся,
                # и в результат уходил вектор ПРЕДЫДУЩЕГО лица из этого же цикла
                # (или падал NameError на первом лице) — из-за этого человек
                # молча матчился с чужим эмбеддингом. Теперь лицо, для которого
                # не удалось посчитать эмбеддинг, просто пропускается целиком,
                # чтобы битый/отсутствующий вектор никогда не попал в сравнение.
                print(f"Ошибка векторизации лица, лицо пропущено: {e}")
                continue

            final_ml_results.append({
                "image_base64": image_base64,
                "face_bytes": face_bytes,
                "bbox": list(map(int, face["bbox"])),
                "score": float(face["score"]),
                "embedding": clean_vector
            })
            
        return final_ml_results

# =====================================================================
# ИНИЦИАЛИЗАЦИЯ И ЗАВИСИМОСТИ FASTAPI (Синглтоны в памяти)
# =====================================================================

# Пути к весам моделей
DETECTOR_PATH = os.path.join("app", "utils", "models_weights", "scrfd_500m_bnkps.onnx")
EMBEDDER_PATH = os.path.join("app", "utils", "models_weights", "w600k_r50.onnx")

# Инициализируем синглтоны один раз при старте приложения
_detector_instance = SCRFDFaceDetector(model_path=DETECTOR_PATH)
_embedder_instance = BuffaloModel(path=EMBEDDER_PATH, use_gpu=False)

def get_ml_service() -> PhotoScanMLService:
    """Провайдер для FastAPI (Depends)"""
    return PhotoScanMLService(
        detector=_detector_instance,
        embedder=_embedder_instance
    )