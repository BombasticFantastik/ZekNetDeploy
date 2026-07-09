import torch
from torch.nn import Module
import faiss
import onnxruntime as ort
import yaml
import cv2
import numpy as np

import os
import PIL


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


option_path = os.path.join(CURRENT_DIR, 'config.yaml')
with open(option_path,'r') as file_option:
    files_option=yaml.safe_load(file_option)

class BuffaloModel(Module):
    def __init__(self, path, use_gpu=False):
        super().__init__()
        self.session=ort.InferenceSession(path)

        self.input_name=self.session.get_inputs()[0].name
        self.output_name=self.session.get_outputs()[0].name
        
    def forward(self, x):
        if isinstance(x, torch.Tensor):
            x_numpy = x.numpy()
        else:
            x_numpy = x
            
        # Нормализация значений
        x_numpy = x_numpy * 255
        x_numpy = (x_numpy - 127.5) / 128.0

        # ИСПРАВЛЕНИЕ: Гарантируем, что на вход ONNX придет строго 4-мерный массив [1, C, H, W]
        if x_numpy.ndim == 2:
            # Если пришла плоская картинка [H, W], добавляем каналы и батч
            x_numpy = np.expand_dims(x_numpy, axis=(0, 1)) # Станет [1, 1, H, W]
        elif x_numpy.ndim == 3:
            # Если пришла картинка с каналами [C, H, W], добавляем размерность батча
            x_numpy = np.expand_dims(x_numpy, axis=0) # Станет [1, C, H, W]

        # Принудительно приводим к типу float32, так как ONNX не любит float64
        x_numpy = x_numpy.astype('float32')

        # Запускаем ONNX сессию
        output = self.session.run([self.output_name], {self.input_name: x_numpy})
        
        output_tensor = torch.from_numpy(output[0])
        output_tensor = torch.nn.functional.normalize(output_tensor, p=2, dim=1)
        
        return output_tensor

class FaceOperations:

    def compare_new_face(img,vectors,model,treshold=1.5):
        """
        ВХОД: Изображения лица,все вектора, модель для векторизации и порог отсечения фото
        ВЫХОД: Индекс наиболее схожего человека из переданного массива векторов
        """

        new_vector=model(img)
        new_vector=new_vector.numpy()

        indexer=faiss.IndexFlatL2(512)
        indexer.add(vectors)

        similarities, indices=indexer.search(x=new_vector,k=1)

        if similarities[0].item()<treshold:
            return indices[0].item()
        else:
            print("ТАКОЙ ЧЕЛОВЕК НЕ НАЙДЕН")
            return 0
            

    def get_vector_from_face(img,model):
        """
        ВХОД: Изображения лица в формате тензора
        ВЫХОД: Вектор лица 
        """

        new_vector=model(img)
        return new_vector.numpy()


    def open_numpy_as_tensor(numpy_img):
        """
        ВХОД: Изображение в формате numpy
        ВЫХОД: Изображение в формате тензора
        """
        rgb_img = cv2.cvtColor(numpy_img, cv2.COLOR_BGR2RGB)
        resized_img = cv2.resize(rgb_img, (112, 112))
        float_img = resized_img.astype('float32') / 255.0
        transposed_img = float_img.transpose(2, 0, 1)
        tensor_img = torch.from_numpy(transposed_img)
        return tensor_img.unsqueeze(0)