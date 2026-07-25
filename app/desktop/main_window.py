import asyncio
import cv2
import httpx
from PySide6.QtWidgets import (QLabel, QMainWindow,
                             QVBoxLayout, QPushButton, QHBoxLayout,
                             QWidget, QTextEdit)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QTimer, Slot
import os
from app.core.config import settings
from app.desktop.attendance_window import AttendanceTableWindow
from app.desktop.units_window import UnitsTableWindow
from app.desktop.users_window import UsersTableWindow
from app.desktop.schedule_window import ScheduleTableWindow


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_PATH = os.path.join(BASE_DIR, "test.png")


def _open_camera():
    stream_url = f"http://{settings.IP_ADDRESS}:{settings.PORT}/mjpegfeed"
    cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)
    if cap.isOpened():
        print("DroidCam MJPEG поток открыт")
        return cap

    print("Камера не найдена — работаю с test.jpg")
    return None


def _read_image(path):
    frame = cv2.imread(path)
    if frame is None:
        print(f"Не удалось загрузить {path}")
    return frame


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        #self.camera = _open_camera()
        self.camera = cv2.VideoCapture(0)
        self.curent_frame = _read_image(IMG_PATH)
        self._raw_test_bytes = self._load_raw_test()
        self.current_unit_id = 1

        self.attendance_table_window = AttendanceTableWindow()
        self.units_table_window = UnitsTableWindow()
        self.users_table_window = UsersTableWindow()
        self.schedule_table_window = ScheduleTableWindow()

        self.client = httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=60.0)

        # правый layout
        self.take_photo_button = QPushButton('Сделать фото и распознать', self)
        self.take_photo_button.clicked.connect(self.on_take_photo_clicked)

        self.test_photo_button = QPushButton('Отправить test.jpg', self)
        self.test_photo_button.clicked.connect(self.on_test_photo_clicked)

        self.log_output = QTextEdit(self)
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Результаты обработки появятся здесь...")

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.take_photo_button)
        right_layout.addWidget(self.test_photo_button)
        right_layout.addWidget(self.log_output)

        # левый layout
        left_layout = QVBoxLayout()

        to_attendance_table_button = QPushButton("Просмотреть посещаемость")
        to_attendance_table_button.clicked.connect(self.show_attendance_table_window)
        to_units_table_button = QPushButton("Просмотреть отряды")
        to_units_table_button.clicked.connect(self.show_units_table_window)
        to_users_table_button = QPushButton("Просмотреть личный состав")
        to_users_table_button.clicked.connect(self.show_users_table_window)
        to_schedule_table_button = QPushButton("Просмотреть дневник посещений")
        to_schedule_table_button.clicked.connect(self.show_schedule_table_window)

        self.image_label = QLabel("нет сигнала")

        left_layout.addWidget(to_attendance_table_button)
        left_layout.addWidget(to_units_table_button)
        left_layout.addWidget(to_users_table_button)
        left_layout.addWidget(to_schedule_table_button)
        left_layout.addWidget(self.image_label)

        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_camera)
        self.timer.start(30)

    # ===================== КАМЕРА / ТЕСТОВОЕ ИЗОБРАЖЕНИЕ =====================

    def _get_frame(self):
        if self.camera is not None:
            success, frame = self.camera.read()
            if success:
                return frame
        frame = _read_image(IMG_PATH)
        if frame is not None:
            self.curent_frame = frame
            return frame
        return None

    def update_camera(self):
        frame = self._get_frame()

        if frame is None:
            self.image_label.setText("нет сигнала")
            return

        self.curent_frame = frame

        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, c = rgb_image.shape

        qt_image = QImage(rgb_image.data, w, h, c * w, QImage.Format_RGB888)
        self.image_label.setPixmap(QPixmap.fromImage(qt_image))

    def _load_raw_test(self):
        try:
            with open(IMG_PATH, 'rb') as f:
                return f.read()
        except Exception:
            return None

    # ===================== ФОТО =====================

    @Slot()
    def on_test_photo_clicked(self):
        if self._raw_test_bytes is None:
            self.log_output.append("test.jpg не найден")
            return
        self.log_output.append("Отправляю test.jpg...")
        self.test_photo_button.setEnabled(False)
        asyncio.ensure_future(self.send_photo_to_backend(self._raw_test_bytes))

    @Slot()
    def on_take_photo_clicked(self):
        if self.curent_frame is None:
            self.log_output.append("Нет кадра — загружаю тестовое изображение")
            self.curent_frame = _read_image(IMG_PATH)
            if self.curent_frame is None:
                self.log_output.append("Ошибка: не удалось загрузить тестовое изображение")
                return

        self.take_photo_button.setEnabled(False)

        if self.camera is None and self._raw_test_bytes is not None:
            image_bytes = self._raw_test_bytes
            self.log_output.append("Использую test.jpg без перекодировки")
        else:
            success, encoded = cv2.imencode('.jpg', self.curent_frame)
            if not success:
                self.log_output.append("Ошибка: не удалось закодировать кадр.")
                self.take_photo_button.setEnabled(True)
                return
            image_bytes = encoded.tobytes()

        asyncio.ensure_future(self.send_photo_to_backend(image_bytes))

    async def send_photo_to_backend(self, image_bytes: bytes):
        self.log_output.append(f"Отправляю unit_id={self.current_unit_id}...")

        try:
            files = {"file": ("webcam_shot.jpg", image_bytes, "image/jpeg")}
            data = {"unit_id": str(self.current_unit_id)}

            with open("gui_test.jpg", "wb") as f:
                f.write(image_bytes)

            response = await self.client.post(
                "/api/v1/photoscan/sessions",
                files=files,
                data=data
            )

            if response.status_code not in (200, 201):
                try:
                    err = response.json()
                except Exception:
                    err = response.text
                self.log_output.append(f"Ошибка бэкенда [{response.status_code}]: {err}")
                return

            result_data = response.json()

            if self.attendance_table_window is not None:
                self.attendance_table_window.update_data(result_data)

            s = result_data.get("summary", {})
            unit = result_data.get("unit", {})
            self.log_output.append("______")
            self.log_output.append(f'Взвод: {unit.get("name", "?")}')
            self.log_output.append(f'Ожидалось: {s.get("expected", 0)} | '
                                   f'Присутствуют: {s.get("present", 0)} | '
                                   f'Отсутствуют: {s.get("absent", 0)}')
            self.log_output.append(f'На фото: {s.get("detected_total", 0)} чел, '
                                   f'из них неизвестных: {s.get("unknown", 0)}')
            self.log_output.append("______")

        except httpx.RequestError as exc:
            self.log_output.append(f"Ошибка сети: {exc}")
        except Exception as exc:
            self.log_output.append(f"Ошибка: {exc}")
        finally:
            self.take_photo_button.setEnabled(True)
            self.test_photo_button.setEnabled(True)

    # ===================== ОКНА =====================

    def show_attendance_table_window(self):
        self.attendance_table_window.show()

    def show_units_table_window(self):
        self.units_table_window.show()

    def show_users_table_window(self):
        self.users_table_window.show()

    def show_schedule_table_window(self):
        self.schedule_table_window.show()

    # ===================== ЗАКРЫТИЕ =====================

    def closeEvent(self, event):
        asyncio.get_event_loop().run_until_complete(self.client.aclose())
        if self.camera is not None:
            self.camera.release()
        event.accept()