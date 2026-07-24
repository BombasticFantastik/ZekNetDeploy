import asyncio
import cv2
import httpx
from PySide6.QtWidgets import (QLabel, QMainWindow, 
                             QVBoxLayout, QPushButton, QHBoxLayout, 
                             QWidget, QTextEdit)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QTimer, Slot,Signal
import os
import sys
from pathlib import Path
from app.core.config import settings
#импорт остальных окон
from app.desktop.attendance_window import AttendanceTableWindow
from app.desktop.units_window import UnitsTableWindow
from app.desktop.users_window import UsersTableWindow
from app.desktop.schedule_window import ScheduleTableWindow



BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))
def get_client(self):
    return httpx.AsyncClient(
        base_url="http://127.0.0.1:18080",
        timeout=10.0
    )
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
stream_url = f"http://{settings.IP_ADDRESS}:{settings.PORT}/mjpegfeed"
img_path = os.path.join(BASE_DIR, "test.jpg")

class MainWindow(QMainWindow):
    data_changed = Signal(str)
    def __init__(self):
        super().__init__()
        
        self.camera = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
        self.camera.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 2000)
        # Это для меня что бы вебку с телефона транслировать, всем остальным сверху код убрать или закомитить, а этот разкомитить!!!
        self.camera = cv2.VideoCapture(0)
        #self.curent_frame = cv2.imread(img_path)
        self.current_unit_id = 1
        self.attendance_table_window=AttendanceTableWindow()
        self.units_table_window=UnitsTableWindow()
        self.users_table_window=UsersTableWindow()
        self.schedule_table_window=ScheduleTableWindow()
        
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
        to_attendance_table_button=QPushButton("Просмотреть посещаемость")
        to_attendance_table_button.clicked.connect(self.show_attendance_table_window)

        to_units_table_button=QPushButton("Просмотреть отряды")
        to_units_table_button.clicked.connect(self.show_units_table_window)

        to_users_table_button=QPushButton("Просмотреть личный состав")
        to_users_table_button.clicked.connect(self.show_users_table_window)

        to_schedule_table_button=QPushButton("Просмотреть дневник посещений")
        to_schedule_table_button.clicked.connect(self.show_schedule_table_window)

        self.image_label = QLabel("нет сигнала")
        

        
        left_layout.addWidget(to_attendance_table_button)
        left_layout.addWidget(to_units_table_button)
        left_layout.addWidget(to_users_table_button)
        left_layout.addWidget(to_schedule_table_button)
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

            if frame is None:
                self.log_output.append("Ошибка: тестовое изображение не найдено")
                return

        self.curent_frame = frame

        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, c = rgb_image.shape

        qt_image = QImage(
            rgb_image.data,
            w,
            h,
            c * w,
            QImage.Format_RGB888
        )

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
        #self.log_output.append("Кодирование изображения...")
        
        #в jpeg
        success, encoded_image = cv2.imencode('.jpg', self.curent_frame)
        if not success:
            self.log_output.append("Ошибка: Не удалось закодировать кадр.")
            self.take_photo_button.setEnabled(True)
            return
            
        image_bytes = encoded_image.tobytes()
        
        asyncio.ensure_future(self.send_photo_to_backend(image_bytes))

        #ФЕЙКОВОЕ оповещение таблицы об обновлении
        # if self.attendance_table_window!=None:
        #     self.attendance_table_window.update_data(fake_json)
        #     self.log_unit_info(fake_json)
        

    async def send_photo_to_backend(self, image_bytes: bytes):
        """Асинхронно отправляет байты изображения на FastAPI"""

        self.log_output.append("Отправка кадра на сервер...")

        try:
            files = {
                "file": (
                    "webcam_shot.jpg",
                    image_bytes,
                    "image/jpeg"
                )
            }

            data = {
                "unit_id": str(self.current_unit_id)
            }

            with open("gui_test.jpg", "wb") as f:
                f.write(image_bytes)
            self.log_output.append(
                f"Отправляю unit_id={self.current_unit_id}"
            )

            response = await self.client.post(
                "/api/v1/photoscan/sessions",
                files=files,
                data=data
            )

            if response.status_code == 200:
                result_data = response.json()
                print(result_data["summary"])
                print(result_data["expected_members"])

                if self.attendance_table_window is not None:
                    self.attendance_table_window.update_data(result_data)

                self.log_unit_info(result_data)

            else:
                try:
                    error_detail = response.json()
                except Exception:
                    error_detail = response.text

                self.log_output.append(
                    f"Ошибка бэкенда [{response.status_code}]: {error_detail}"
                )

        except httpx.RequestError as exc:
            self.log_output.append(
                f"Ошибка сети при связи с бэкендом: {exc}"
            )

        except Exception as exc:
            self.log_output.append(
                f"Ошибка обработки: {exc}"
            )

        finally:
            self.take_photo_button.setEnabled(True)

    def closeEvent(self, event):
        """Срабатывает при закрытии окна программы"""

        asyncio.get_event_loop().run_until_complete(self.client.aclose())

        self.camera.release()
        event.accept()

    def log_unit_info(self,result_data):
        self.log_output.append('______')
        self.log_output.append(f'Вывод информации о взводе "{result_data["unit"]["name"]}":')
        self.log_output.append(f'Ожидалось {result_data["summary"]["expected"]} людей')
        self.log_output.append(f'Присутствуют {result_data["summary"]["present"]} людей')
        self.log_output.append(f'Отсутствуют {result_data["summary"]["absent"]} людей')
        self.log_output.append("")
        self.log_output.append(f'На фото присутсвует {result_data["summary"]["detected_total"]} человек')
        self.log_output.append(f'Среди них {result_data["summary"]["unknown"]} неизвестных людей')
        self.log_output.append('______')

    def show_attendance_table_window(self):
        self.attendance_table_window.show()
    def show_units_table_window(self):
        self.units_table_window.show()
    def show_users_table_window(self):
        self.users_table_window.show()
    def show_schedule_table_window(self):
        self.schedule_table_window.show()