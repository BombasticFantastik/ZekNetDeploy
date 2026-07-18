import sys
import asyncio
import cv2
import httpx
from PySide6.QtWidgets import (QApplication, QLabel, QMainWindow, 
                             QVBoxLayout, QPushButton, QHBoxLayout, QWidget, QTextEdit,QTableWidget,QTableWidgetItem,QAbstractItemView,QHeaderView)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QTimer, Slot,Qt,Signal
#from photoloader import PhotoLoader

import qasync  
import os
#from test import fake_json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
img_path = os.path.join(BASE_DIR, "test.jpg")

class MainWindow(QMainWindow):
    data_changed = Signal(str)
    def __init__(self):
        super().__init__()
        
        self.camera = cv2.VideoCapture(-1)
        self.curent_frame = None
        self.table_window=TableWindow()
        
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
        to_table_button=QPushButton("Просмотреть посещаемость")
        to_table_button.clicked.connect(self.show_table_window)
        self.image_label = QLabel("нет сигнала")
        

        
        left_layout.addWidget(to_table_button)
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

        #ФЕЙКОВОЕ оповещение таблицы об обновлении
        # if self.table_window!=None:
        #     self.table_window.update_data(fake_json)
        

    async def send_photo_to_backend(self, image_bytes: bytes):
        """Асинхронно отправляет байты изображения на FastAPI"""
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


                #оповещение таблицы об обновлении
                if self.table_window!=None:
                    self.table_window.update_data(result_data)
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

    def show_table_window(self):
        self.table_window.show()
        
class TableWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Присутствующие")
        self.all_persons = []
        self.resize(1200, 800) 
        
        self.BASE_IMAGE_URL = "http://127.0.0.1:8000/static/"
        self.client = httpx.AsyncClient(timeout=10.0)

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0) 

        self.table = QTableWidget()
        self.table.setRowCount(0)
        self.table.setColumnCount(5)
        
        headers = ['ФИО', 'Лицо на фото', "Фото в базе", "Дистанция","Статус"]
        self.table.setHorizontalHeaderLabels(headers)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch) 
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.verticalHeader().setDefaultSectionSize(75)
        self.table.verticalHeader().setVisible(False)
        
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        right_layout.addWidget(self.table)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(10) 
        
        close_button = QPushButton("Закрыть окно")
        close_button.setFixedWidth(120) 
        close_button.clicked.connect(self.close_this_window)
        
        left_layout.addWidget(close_button)
        left_layout.addStretch() 

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15) 
        main_layout.setSpacing(15) 
        
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)

        self.setLayout(main_layout)
        
    def close_this_window(self):
        self.close()

    def update_data(self, result_data):
        # 1. Фильтруем и добавляем только уникальных
        names = [person['fio'] for person in self.all_persons]
        for person in result_data.get('expected_members', []):
            if person['fio'] not in names:
                self.all_persons.append(person)

        photos=[person['cropped_photo'] for person in self.all_persons]
        for person in result_data.get('unexpected_members', []):
            if person['cropped_photo'] not in photos:
                self.all_persons.append(person)

        # 2. Сбрасываем строки таблицы
        self.table.setRowCount(0)
        
        # 3. Заполняем таблицу заново
        for i, person in enumerate(self.all_persons):
            self.table.insertRow(i) 
            
            #фио
            person_name = QTableWidgetItem(str(person['fio']))
            self.table.setItem(i, 0, person_name)
            
            #фото лица
            label_cropped = QLabel("Загрузка...")
            label_cropped.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(i, 1, label_cropped)
            
            #шаблон лица
            label_etalon = QLabel("Загрузка...")
            label_etalon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(i, 2, label_etalon)
            
            #дистанция
            person_distance = QTableWidgetItem(f"{person['distance']:}"[:5])
            self.table.setItem(i, 3, person_distance)

            #статус
            person_status=QTableWidgetItem(f"{person['status']:}")
            self.table.setItem(i, 4, person_status)

            url_cropped = f"{self.BASE_IMAGE_URL}{person['cropped_photo']}"
            url_etalon = f"{self.BASE_IMAGE_URL}{person['etalon_photo']}"
            
            asyncio.ensure_future(self.fetch_and_render_image(url_cropped, label_cropped))
            asyncio.ensure_future(self.fetch_and_render_image(url_etalon, label_etalon))

    async def fetch_and_render_image(self, url: str, target_label: QLabel):
        """Асинхронно скачивает картинку через httpx и вставляет в QLabel ячейки"""
        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                
                if not pixmap.isNull():
                    # Красиво сжимаем под размер ячейки таблицы
                    scaled = pixmap.scaled(70, 70, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    target_label.setPixmap(scaled)
                else:
                    target_label.setText("Ошибка формата")
            else:
                target_label.setText(f"ошибка {response.status_code}")
        except Exception as e:
            target_label.setText("Ошибка сети")

    def closeEvent(self, event):
        asyncio.ensure_future(self.client.aclose())
        event.accept()

if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    window = MainWindow()
    window.show()
    
    with loop:
        loop.run_forever()