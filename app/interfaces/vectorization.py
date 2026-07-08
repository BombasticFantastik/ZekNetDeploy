from app.utils.vectorization import compare_new_face, open_numpy_as_tensor, get_vector_from_face
import numpy as np
import cv2
from app.utils.image_processing import init_detector, detect_faces
from app.utils.vectorization import BuffaloModel

class ImageComparisonService():
    def __init__(self):
          pass

    def open_bytes_as_numpy(self,file_bytes:bytes)->np.ndarray: 
        """
        Открывает набор байт как numpy array
        """            
        nparr = np.frombuffer(file_bytes, np.uint8) 
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Не удалось декодировать изображение из байт")
        return image
    
    def get_vector_from_numpy(self,image:np.ndarray,embedder:BuffaloModel)->list: 
        """
        Извлекает вектор из numpy изображения лица и превращает в список,
        """            
        face_tensor = open_numpy_as_tensor(image) 
        face_vector = get_vector_from_face(face_tensor,embedder ) 
        face_embedding = face_vector.flatten().tolist()
        return face_embedding
    
    def get_vector_from_bytes(self,file_bytes:bytes,embedder:BuffaloModel)->list: 
        """
        Извлекает вектор из набора байт изображения лица и превращает в список,
        """            
        nparr = np.frombuffer(file_bytes, np.uint8) 
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        face_tensor = open_numpy_as_tensor(image) 
        face_vector = get_vector_from_face(face_tensor,embedder ) 
        face_embedding = face_vector.flatten().tolist()
        return face_embedding
    
    def open_numpy_as_bytes(self,face_numpy:np.ndarray)->bytes:

        success, encoded_face = cv2.imencode(".jpg", face_numpy) 
        if not success:
            pass
        face_bytes = encoded_face.tobytes() 
        return face_bytes
    
    def detect_and_get_faces(self, image: np.ndarray|bytes,detector,embedder:BuffaloModel) -> dict:
            """Принимает изображение взвода в формате numpy или набора байтов .
            Возвращает словарь с метками:
            image - bytes
            bbox: list(int),
            score": float,
            embedding": list         
            """

            if type(image)==bytes:
                 image=self.open_bytes_as_numpy(image)
                 
            detected_faces = detect_faces(
                image=image,
                detector=detector,
                conf_thresh=0.25
            )

            faces = []

            for face in detected_faces:
                face_numpy = face["image"]
                face_tensor = open_numpy_as_tensor(face_numpy)
                face_vector = get_vector_from_face(face_tensor, embedder)
                clean_vector = face_vector.flatten().tolist()


                faces.append({
                    "image": cv2.imencode(".jpg", face["image"]).tobytes(),
                    "bbox": list(map(int, face["bbox"])),
                    "score": float(face["score"]),
                    "embedding": clean_vector
                })

            return faces
    
    


    
image_compare_service=ImageComparisonService()