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

class VectorizationModel(Module):
    def __init__(self, path,use_gpu=False):
        super().__init__()
        opts=ort.SessionOptions()
        opts.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_ALL#максимальная оптимизация графа
        
        opts.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
        #opts.intra_op_num_threads=get_optimal_threads()

        opt_path = path.replace('.onnx', '_optimized.onnx')
        if not os.path.exists(opt_path):
            opts.optimized_model_filepath=opt_path#оптимизируем модель по пути

        providers=['CUDAExecutionProvider', 'CPUExecutionProvider'] if use_gpu else ['CPUExecutionProvider']

        model_to_load=opt_path if os.path.exists(opt_path) else path
            

        self.session=ort.InferenceSession(model_to_load,opts,providers=providers)

        self.input_name=self.session.get_inputs()[0].name
        self.output_name=self.session.get_outputs()[0].name
    def forward(self,x):

        if isinstance(x, torch.Tensor):
            x_numpy = x.detach().cpu().numpy()
        else:
            x_numpy = np.array(x, copy=False)

        x_numpy = x_numpy.astype(np.float32)

        if x_numpy.ndim == 3:
            if x_numpy.shape[-1] in (1, 3):
                x_numpy = np.transpose(x_numpy, (2, 0, 1))
            x_numpy = np.expand_dims(x_numpy, axis=0)
        elif x_numpy.ndim == 2:
            x_numpy = np.expand_dims(x_numpy, axis=(0, 1))

        if x_numpy.max()>1.0:
            x_numpy=x_numpy/255.0
        x_numpy = (x.numpy()-0.5)/0.5

        output=self.session.run([self.output_name],{self.input_name:x_numpy})
        output=torch.from_numpy(output[0])
        output = torch.nn.functional.normalize(output, p=2, dim=1)
        return output
    

class FaceOperations:
    def compare_new_face(self, img,vectors,model,treshold=1.5):
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
            

    def get_vector_from_face(self, img,model):
        """
        ВХОД: Изображения лица в формате тензора
        ВЫХОД: Вектор лица 
        """

        new_vector=model(img)
        return new_vector.numpy()


    def open_numpy_as_tensor(self, numpy_img):
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