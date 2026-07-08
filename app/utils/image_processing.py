import os
import logging
import cv2
import numpy as np
from insightface.model_zoo import get_model

from app.interfaces.image_processing import FaceDetectorInterface, DetectedFaceDict

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class SCRFDFaceDetector(FaceDetectorInterface):
    def __init__(self, model_path: str, target_size: int = 2048):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Файл модели '{model_path}' не найден.")
            
        logging.info(f"Инициализация модели: {model_path}")
        self.detector = get_model(model_path, providers=["CPUExecutionProvider"])
        self.detector.prepare(ctx_id=-1, input_size=(target_size, target_size), nms_thresh=0.4)

    def detect_faces(self, image: np.ndarray, conf_thresh: float = 0.25) -> list[DetectedFaceDict]:
        if image is None:
            raise ValueError("Не удалось открыть изображение.")
            
        orig_h, orig_w = image.shape[:2]
        BORDER = 150
        
        # Добавляем поля, чтобы детектор не пропускал лица у края кадра
        padded_img = cv2.copyMakeBorder(
            image, BORDER, BORDER, BORDER, BORDER, 
            cv2.BORDER_CONSTANT, value=(0, 0, 0)
        )
        
        logging.info(f"Детекция на изображении ({orig_w}x{orig_h})")
        bboxes, kpss = self.detector.detect(padded_img, max_num=0, metric="max")
        
        if bboxes is None or len(bboxes) == 0:
            logging.warning("Лица не найдены.")
            return []
            
        scores = bboxes[:, 4]
        rects = bboxes[:, :4]
        
        faces: list[DetectedFaceDict] = []
        
        for i, bbox in enumerate(rects):
            score = float(scores[i])
            if score < conf_thresh:
                continue
                
            x1, y1, x2, y2 = map(int, bbox)
            
            # 1. Пересчитываем координаты для оригинального изображения 
            # и жестко ограничиваем их реальными рамками кадра
            orig_x1 = max(0, x1 - BORDER)
            orig_y1 = max(0, y1 - BORDER)
            orig_x2 = min(orig_w, x2 - BORDER)
            orig_y2 = min(orig_h, y2 - BORDER)
            
            # Проверка на вырождение bounding box'а
            if orig_x2 <= orig_x1 or orig_y2 <= orig_y1:
                continue

            # 2. Делаем кроп прямо из ОРИГИНАЛЬНОГО изображения.
            # КРИТИЧНОЕ ИСПРАВЛЕНИЕ: используем .copy() для создания C-contiguous массива,
            # иначе ONNX/cv2.resize прочитают мусор из памяти и выдадут одинаковые пустые вектора
            face_img = image[orig_y1:orig_y2, orig_x1:orig_x2].copy()
            
            if face_img.size == 0:
                continue
                
            # 3. Пересчитываем сдвиг ключевых точек
            # kpss даны для padded_img. Точка (0,0) нашего кропа на padded_img 
            # находится по координатам (orig_x1 + BORDER, orig_y1 + BORDER)
            shifted_kps = kpss[i] - np.array([BORDER + orig_x1, BORDER + orig_y1])
            
            faces.append({
                "image": face_img,                             # Плотный, независимый в памяти кроп
                "score": score,
                "bbox": (orig_x1, orig_y1, orig_x2, orig_y2),  # Чистые координаты для БД
                "kps": shifted_kps
            })
            
        logging.info(f"Детекция завершена. Найдено лиц: {len(faces)}")
        return faces