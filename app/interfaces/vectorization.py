from abc import ABC, abstractmethod
from typing import Any, Union
import numpy as np
import torch
from numpy.typing import NDArray


FaceVector = NDArray[np.float32]


class BuffaloModelInterface(ABC):
    """Интерфейс для векторизации лиц на базе ONNX-модели Buffalo."""

    @abstractmethod
    def __init__(self, path: str, use_gpu: bool = False) -> None:
        """Инициализация сессии модели по указанному пути."""
        pass

    @abstractmethod
    def forward(self, x: Union[torch.Tensor, NDArray[np.float32]]) -> torch.Tensor:
        """
        Принимает тензор или numpy-массив, нормализует, 
        запускает ONNX сессию и возвращает нормированный тензор признаков.
        """
        pass


class FaceOperationsInterface(ABC):
    """Интерфейс для операций над изображениями и векторами лиц."""

    @abstractmethod
    def open_numpy_as_tensor(self, numpy_img: NDArray[np.uint8]) -> torch.Tensor:
        """
        ВХОД: Изображение в формате numpy (BGR).
        ВЫХОД: Предобработанное изображение в формате тензора [1, C, H, W].
        """
        pass

    @abstractmethod
    def get_vector_from_face(self, img: torch.Tensor, model: BuffaloModelInterface) -> FaceVector:
        """
        ВХОД: Изображения лица в формате тензора.
        ВЫХОД: Вектор лица в формате numpy array.
        """
        pass

    @abstractmethod
    def compare_new_face(
        self, 
        img: torch.Tensor, 
        vectors: FaceVector, 
        model: BuffaloModelInterface, 
        treshold: float = 1.5
    ) -> int:
        """
        ВХОД: Изображение лица, все вектора, модель для векторизации и порог отсечения фото.
        ВЫХОД: Индекс наиболее схожего человека из переданного массива векторов.
        """
        pass