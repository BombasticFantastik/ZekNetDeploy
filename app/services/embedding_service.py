import numpy as np
from app.interfaces.vectorization import BuffaloModelInterface, FaceOperationsInterface
import cv2

class EmbeddingMLService:
    def __init__(self, embedder: BuffaloModelInterface, face_operations: FaceOperationsInterface):
        self.embedder = embedder
        self.face_operations = face_operations

    def create_embedding(self, image_bytes) -> list[float]:
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError("Invalid image")

        tensor = self.face_operations.open_numpy_as_tensor(image)
        vector = self.face_operations.get_vector_from_face(tensor, self.embedder)

        return vector.flatten().tolist()