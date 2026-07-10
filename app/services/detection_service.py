import base64
from typing import TypedDict, List
import cv2
import numpy as np

# Твои импорты интерфейсов и детектора
from app.interfaces.image_processing import FaceDetectorInterface

# Импорты эмбеддера напарника
from app.interfaces.vectorization import BuffaloModelInterface, FaceOperationsInterface


class ProcessedFaceResult(TypedDict):
    image_base64: str
    face_bytes: bytes
    bbox: list[int]
    score: float
    embedding: list[float]


class PhotoScanMLService:
    def __init__(
            self, 
            detector: FaceDetectorInterface, 
            embedder: BuffaloModelInterface,
            face_operations: FaceOperationsInterface
    ):
        self.detector = detector
        self.embedder = embedder
        self.face_operations = face_operations

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
                tensor_img = self.face_operations.open_numpy_as_tensor(face_numpy)
                
                # Извлекаем эмбеддинг
                vector_np = self.face_operations.get_vector_from_face(tensor_img, self.embedder)
                
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
