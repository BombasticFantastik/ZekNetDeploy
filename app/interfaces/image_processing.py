from abc import ABC, abstractmethod
from typing import Any, TypedDict
import numpy as np

class DetectedFaceDict(TypedDict):
    image: np.ndarray
    score: float
    bbox: tuple[int, int, int, int]
    kps: Any

class FaceDetectorInterface(ABC):
    
    @abstractmethod
    def detect_faces(self, image: np.ndarray, conf_thresh: float = 0.25) -> list[DetectedFaceDict]:
        """
        Принимает изображение в формате numpy array.
        Находит лица и возвращает список словарей с кропом, скором, bbox и ключевыми точками.
        """
        pass