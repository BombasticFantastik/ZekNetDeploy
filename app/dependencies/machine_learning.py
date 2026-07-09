from fastapi import Depends

from app.core.cv_engine import CVEngine, get_cv_engine
from app.services.detection_service import PhotoScanMLService

from app.interfaces.vectorization import FaceOperationsInterface
from app.utils.vectorization import open_numpy_as_tensor, get_vector_from_face, compare_new_face


class FaceOperations(FaceOperationsInterface):
    
    def open_numpy_as_tensor(self, numpy_img):
        return open_numpy_as_tensor(numpy_img)

    def get_vector_from_face(self, img, model):
        return get_vector_from_face(img, model)

    def compare_new_face(self, img, vectors, model, treshold=1.5):
        return compare_new_face(
            img,
            vectors,
            model,
            treshold
        )
    

def get_ml_service(engine: CVEngine = Depends(get_cv_engine)) -> PhotoScanMLService:
    """Фабрика движка сервиса"""
    face_operations = FaceOperations()


    return PhotoScanMLService(
        detector=engine.detector,
        embedder=engine.embedder,
        face_operatorions=face_operations
    )