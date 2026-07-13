import os

from app.core.config import settings

from app.utils.image_processing import SCRFDFaceDetector
from app.utils.vectorization import BuffaloModel
from app.utils.vectorization import FaceOperations

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)


class CVEngine:
    def __init__(self):
        self.detector_path = os.path.join(
            BASE_DIR,
            "utils/models_weights/scrfd_500m_bnkps.onnx"
        )
        self.embedder_path = os.path.join(
            BASE_DIR,
            "utils/models_weights/adaface_ir101.onnx"
        )

        self.detector = SCRFDFaceDetector(model_path=self.detector_path, target_size=2048)
        self.embedder = BuffaloModel(path=self.embedder_path, use_gpu=False)
        self.face_operations = FaceOperations()


_cv_instance: CVEngine | None = None


async def init_cv_engine():
    global _cv_instance
    _cv_instance = CVEngine()


async def close_cv_engine():
    global _cv_instance
    _cv_instance = None


def get_cv_engine() -> CVEngine:
    if _cv_instance is None:
        raise RuntimeError("Error was raised on CVEngine init")
    return _cv_instance