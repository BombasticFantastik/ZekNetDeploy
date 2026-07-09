import os
import cv2
import numpy as np
import base64

from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import settings
from app.services.detection_service import SCRFDFaceDetector
from app.utils.vectorization import BuffaloModel

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

# def encode(img):
#     _, buffer = cv2.imencode(".jpg", img)
#     return base64.b64encode(buffer).decode("utf-8")

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

        self.detector = SCRFDFaceDetector(model_path=self.detector_path, target_size=2048)
        self.embedder = BuffaloModel(path=self.embedder_path, use_gpu=False)


_cv_instance: CVEngine | None = None


async def init_cv_engine():
    global _cv_instance
    _cv_instance = CVEngine


async def close_cv_engine():
    global _cv_instance
    _cv_instance = None


def get_cv_engine() -> CVEngine:
    if _cv_instance is None:
        raise RuntimeError("Error was raised on CVEngine init")
    return _cv_instance