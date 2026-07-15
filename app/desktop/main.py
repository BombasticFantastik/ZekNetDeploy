import sys
import asyncio
import cv2
import httpx
from PySide6.QtWidgets import (QApplication, QLabel, QMainWindow, 
                             QVBoxLayout, QPushButton, QHBoxLayout, QWidget, QTextEdit)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QTimer, Slot
import qasync  
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
img_path = os.path.join(BASE_DIR, "test.jpg")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.camera = cv2.VideoCapture(-1)
        self.curent_frame = None
        
        #http
        self.client = httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=60.0)

        
        #правый layout
        self.take_photo_button = QPushButton('Сделать фото и распознать', self)
        self.take_photo_button.clicked.connect(self.on_take_photo_clicked)
        
        self.log_output = QTextEdit(self)
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Результаты обработки появятся здесь...")
        
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.take_photo_button)
        right_layout.addWidget(self.log_output)

        #левый layout
        left_layout = QVBoxLayout()
        self.image_label = QLabel("нет сигнала")
        left_layout.addWidget(self.image_label)

        #сборка
        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        #таймер
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_camera)
        self.timer.start(30)

    def update_camera(self):
        """Регулярно забирает кадр с камеры и выводит на экран"""
        success, frame = self.camera.read()
        if not success:
            frame = cv2.imread(img_path)

        if success:
            self.curent_frame = frame
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, c = rgb_image.shape
            qt_image = QImage(rgb_image.data, w, h, c * w, QImage.Format_RGB888)
            self.image_label.setPixmap(QPixmap.fromImage(qt_image))

    @Slot()
    def on_take_photo_clicked(self):
        """Обрабатывает нажатие кнопки «Сделать фото»"""
        if self.curent_frame is None:
            self.log_output.append("Нет кадра — загружаю тестовое изображение")
            self.curent_frame = cv2.imread(img_path)

            if self.curent_frame is None:
                self.log_output.append("Ошибка: не удалось загрузить тестовое изображение")
                return
        
        
        self.take_photo_button.setEnabled(False)
        self.log_output.append("Кодирование изображения...")
        
        #в jpeg
        success, encoded_image = cv2.imencode('.jpg', self.curent_frame)
        if not success:
            self.log_output.append("Ошибка: Не удалось закодировать кадр.")
            self.take_photo_button.setEnabled(True)
            return
            
        image_bytes = encoded_image.tobytes()
        
        asyncio.ensure_future(self.send_photo_to_backend(image_bytes))

    async def send_photo_to_backend(self, image_bytes: bytes):
        """Асинхронно отправляет байты изображения на твой роут FastAPI"""
        self.log_output.append("Отправка кадра на сервер...")
        
        try:
            files = {
                "file": ("webcam_shot.jpg", image_bytes, "image/jpeg")
            }
            
            url_path = "/api/v1/photoscan/save_&_scan_&_compare"
            response = await self.client.post(url_path, files=files)
            
            if response.status_code == 200:
                result_data = response.json()
                self.log_output.append("Фото успешно обработано!")
                self.log_output.append(f"Ответ бэкенда:\n{result_data}")
            else:
                try:
                    error_detail = response.json()
                except Exception:
                    error_detail = response.text
                self.log_output.append(f"ошибка бэкенда [{response.status_code}]: {error_detail}")
                
        except httpx.RequestError as exc:
            self.log_output.append(f"ошибка сети при связи с бэкендом: {exc}")
        finally:
            self.take_photo_button.setEnabled(True)

    def closeEvent(self, event):
        """Срабатывает при закрытии окна программы"""

        asyncio.get_event_loop().run_until_complete(self.client.aclose())

        self.camera.release()
        event.accept()


if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    window = MainWindow()
    window.show()
    
    with loop:
        loop.run_forever()