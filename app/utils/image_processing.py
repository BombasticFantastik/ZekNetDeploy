import os
import logging
import cv2
import numpy as np
from insightface.model_zoo import get_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def init_detector(model_path, target_size=2048):
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Файл модели '{model_path}' не найден.")
        
    logging.info(f"Инициализация модели: {model_path}")
    detector = get_model(model_path, providers=["CPUExecutionProvider"])
    
    # nms_thresh установлен в 0.4 для лучшего отсечения дублирующих рамок
    detector.prepare(
        ctx_id=-1,
        input_size=(target_size, target_size),
        nms_thresh=0.4
    )
    return detector


def detect_faces(image, detector, conf_thresh=0.25):
    """
    Загружает изображение, находит лица и возвращает список словарей,
    содержащих вырезанные изображения лиц (массивы numpy).
    """
    orig_img = image
    if orig_img is None:
        raise ValueError(f"Не удалось открыть изображение '{image}'.")

    orig_h, orig_w = orig_img.shape[:2]

    # Рамка, чтобы детектор не терял лица у самых краев кадра
    BORDER = 150
    padded_img = cv2.copyMakeBorder(
        orig_img, BORDER, BORDER, BORDER, BORDER,
        cv2.BORDER_CONSTANT, value=(0, 0, 0)
    )

    logging.info(f"Детекция на {image} ({orig_w}x{orig_h})")
    
    # КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Используем metric="max", чтобы включить 
    # максимальное подавление дубликатов на больших разрешениях
    bboxes, kpss = detector.detect(padded_img, max_num=0, metric="max")

    if bboxes is None or len(bboxes) == 0:
        logging.warning("Лица не найдены.")
        return []

    scores = bboxes[:, 4]
    rects = bboxes[:, :4]
    faces = []

    for i, bbox in enumerate(rects):
        score = float(scores[i])

        if score < conf_thresh:
            continue

        x1, y1, x2, y2 = map(int, bbox)
        
        # Перенос координат обратно (вычитаем рамку)
        x1 -= BORDER
        y1 -= BORDER
        x2 -= BORDER
        y2 -= BORDER
        
        # Ограничиваем базовыми рамками оригинального разрешения
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(orig_w, x2), min(orig_h, y2)

        if x2 <= x1 or y2 <= y1:
            continue

        crop_x1 = max(0, x1)
        crop_y1 = max(0, y1)
        crop_x2 = min(orig_w, x2)
        crop_y2 = min(orig_h, y2)

        # Вырезаем фрагмент лица из оригинального изображения в памяти
        face_img = orig_img[crop_y1:crop_y2, crop_x1:crop_x2]
        
        if face_img.size == 0:
            continue

        # Перенос координат ключевых точек относительно вырезанного фрагмента
        shifted_kps = kpss[i] - np.array([BORDER + crop_x1, BORDER + crop_y1])

        faces.append({
            "image": face_img,         
            "score": score,            
            "bbox": (crop_x1, crop_y1, crop_x2, crop_y2), 
            "kps": shifted_kps         
        })

    logging.info(f"Детекция завершена. Найдено лиц: {len(faces)} (из {len(bboxes)} гипотез)")
    return faces


if __name__ == "__main__":
    MODEL_FILE = "scrfd_500m_bnkps.onnx"
    INPUT_IMAGE = "faces/group_photo.png"
    
    try:
        face_detector = init_detector(MODEL_FILE, target_size=2048)
        
        detected_faces = detect_faces(
            image=INPUT_IMAGE,
            detector=face_detector,
            conf_thresh=0.25
        )
        
        # 1. Сначала выводим инфо о всех найденных лицах в консоль
        for idx, face in enumerate(detected_faces):
            current_face_img = face["image"]
            print(
                f"Лицо #{idx + 1}: "
                f"Score: {face['score']:.2f} | "
                f"Размер кропа: {current_face_img.shape[1]}x{current_face_img.shape[0]} | "
                f"Тип: {type(current_face_img)}"
            )
    
    except Exception as e:
        logging.error(f"Критический сбой скрипта: {e}", exc_info=True)