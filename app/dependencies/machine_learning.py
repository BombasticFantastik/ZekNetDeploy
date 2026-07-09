from fastapi import Depends

from app.core.cv_engine import CVEngine, get_cv_engine
from app.services.detection_service import PhotoScanMLService
    

def get_ml_service(engine: CVEngine = Depends(get_cv_engine)) -> PhotoScanMLService:
    """Фабрика движка сервиса"""
    return PhotoScanMLService(
        detector=engine.detector,
        embedder=engine.embedder,
        face_operations=engine.face_operations
    )