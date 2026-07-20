import sys
import asyncio
import cv2
import httpx
from PySide6.QtWidgets import (QApplication, QLabel, QMainWindow, 
                             QVBoxLayout, QPushButton, QHBoxLayout, 
                             QWidget, QTextEdit,QTableWidget,QTableWidgetItem,
                             QAbstractItemView,QHeaderView,QLineEdit,QFileDialog)
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
        
        self.camera = None
        self.curent_frame = cv2.imread(img_path)
        self.current_unit_id = 1
        self.attendance_table_window=AttendanceTableWindow()
        self.units_table_window=UnitsTableWindow()
        self.users_table_window=UsersTableWindow()
        
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

        self.image_label = QLabel("нет сигнала")
        

        
        left_layout.addWidget(to_attendance_table_button)
        left_layout.addWidget(to_units_table_button)
        left_layout.addWidget(to_users_table_button)
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

        # success, frame = self.camera.read()
        success = None

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
                "/api/v1/photoscan/scan_save_report",
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

class AttendanceTableWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Присутствующие")
        self.all_persons = []
        self.resize(1200, 800) 
        
        self.BASE_IMAGE_URL = "http://127.0.0.1:8000/api/v1/bucket_loader/image/"
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
        def get_photo_path(photo):
            if isinstance(photo, dict):
                return photo.get("path")
            return photo

        cropped_photos = [
            get_photo_path(person.get("cropped_photo"))
            for person in self.all_persons
        ]

        for person in result_data.get("expected_members", []):
            photo_path = get_photo_path(person.get("cropped_photo"))

            if photo_path and photo_path not in cropped_photos:
                self.all_persons.append(person)
                cropped_photos.append(photo_path)

        for person in result_data.get("unexpected_members", []):
            photo_path = get_photo_path(person.get("cropped_photo"))

            if photo_path and photo_path not in cropped_photos:
                self.all_persons.append(person)
                cropped_photos.append(photo_path)

        self.table.setRowCount(0)

        for i, person in enumerate(self.all_persons):
            self.table.insertRow(i)

            # ФИО
            self.table.setItem(
                i,
                0,
                QTableWidgetItem(str(person.get("fio") or "Неизвестный"))
            )

            # Лицо
            label_cropped = QLabel("Нет фото")
            label_cropped.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(i, 1, label_cropped)

            # Эталон
            label_etalon = QLabel("Нет фото")
            label_etalon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(i, 2, label_etalon)

            # Дистанция
            distance = person.get("distance")

            self.table.setItem(
                i,
                3,
                QTableWidgetItem(
                    f"{distance:.4f}" if distance is not None else "-"
                )
            )

            # Статус
            self.table.setItem(
                i,
                4,
                QTableWidgetItem(str(person.get("status")))
            )

            # Фото лица
            cropped = person.get("cropped_photo")

            if isinstance(cropped, dict):
                url_cropped = (
                    f"{self.BASE_IMAGE_URL}"
                    f"{cropped['bucket']}/"
                    f"{cropped['path']}"
                )

                asyncio.ensure_future(
                    self.fetch_and_render_image(
                        url_cropped,
                        label_cropped
                    )
                )

            # Эталонное фото
            etalon = person.get("etalon_photo")

            if isinstance(etalon, dict):
                url_etalon = (
                    f"{self.BASE_IMAGE_URL}"
                    f"{etalon['bucket']}/"
                    f"{etalon['path']}"
                )

                asyncio.ensure_future(
                    self.fetch_and_render_image(
                        url_etalon,
                        label_etalon
                    )
                )

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

class UnitsTableWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Отряды")
        self.all_persons = []
        self.resize(1200, 800) 
        
        self.client = httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=10.0)

        # правый layout
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0) 

        self.table = QTableWidget()
        self.table.setRowCount(0)
        # Увеличили количество колонок до 3
        self.table.setColumnCount(3)
        
        # Добавили заголовок для удаления
        headers = ['Id', 'Название отряда', 'Действие']
        self.table.setHorizontalHeaderLabels(headers)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) 
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Кнопка удаления будет компактной
        
        self.table.verticalHeader().setDefaultSectionSize(75)
        self.table.verticalHeader().setVisible(False)
        
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        right_layout.addWidget(self.table)

        # левый layout
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10) 

        # Кнопка закрытия
        close_button = QPushButton("Закрыть окно")
        close_button.setFixedWidth(120) 
        close_button.clicked.connect(self.close_this_window)
        
        left_layout.addWidget(close_button)
        left_layout.addStretch() 
        
        # Форма создания нового отряда
        self.unit_name_input = QLineEdit()
        self.unit_name_input.setPlaceholderText("Имя нового отряда...")
        self.unit_name_input.setFixedWidth(150)
        
        create_button = QPushButton("Создать отряд")
        create_button.setFixedWidth(150)
        create_button.clicked.connect(self.create_new_unit)
        
        left_layout.addWidget(self.unit_name_input)
        left_layout.addWidget(create_button)
        left_layout.addSpacing(20) 

        # Главный контейнер
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15) 
        main_layout.setSpacing(15) 
        
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)

        self.setLayout(main_layout)
        
    def close_this_window(self):
        self.close()

    def create_new_unit(self):
        """Слот кнопки: валидирует ввод и запускает асинхронный POST"""
        name = self.unit_name_input.text().strip()
        if not name:
            return
            
        asyncio.ensure_future(self.send_create_request(name))

    async def send_create_request(self, name):
        """Отправка POST-запроса на создание отряда"""
        url_path = "/api/v1/unit_creator/"
        try:
            response = await self.client.post(url_path, json={"name": name})
            if response.status_code in (200, 201):
                self.unit_name_input.clear()
                await self.update_data() 
            else:
                print(f"Ошибка бэкенда при создании: {response.status_code}")
        except Exception as e:
            print(f"Ошибка сети/запроса при создании: {e}")

    async def update_data(self, result_data=None):
        """Асинхронное получение данных и заполнение таблицы"""
        url_path = "/api/v1/unit_creator/"
        try:
            response = await self.client.get(url_path)
            result_data = response.json()

            self.table.setRowCount(0)
            for i, unit in enumerate(result_data.get('units', [])):
                self.table.insertRow(i) 
                
                # id
                unit_id_item = QTableWidgetItem(str(unit['id']))
                self.table.setItem(i, 0, unit_id_item)
                            
                # имя
                unit_name_item = QTableWidgetItem(f"{unit['name']}")
                self.table.setItem(i, 1, unit_name_item)

                # Кнопка удаления в третью колонку
                delete_button = QPushButton("Удалить")
                # Используем lambda с фиксацией текущего unit['id'], чтобы не стирались ссылки в цикле
                unit_id = unit['id']
                delete_button.clicked.connect(lambda checked, uid=unit_id: self.delete_unit(uid))
                
                # Центрируем кнопку в ячейке для красоты
                container = QWidget()
                layout = QHBoxLayout(container)
                layout.addWidget(delete_button)
                layout.setContentsMargins(5, 5, 5, 5)
                layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                container.setLayout(layout)
                
                self.table.setCellWidget(i, 2, container)

        except Exception as e:
            print(f"Ошибка при обновлении таблицы: {e}")

    def delete_unit(self, unit_id):
        """Слот кнопки удаления: запускает асинхронный DELETE запрос"""
        asyncio.ensure_future(self.send_delete_request(unit_id))

    async def send_delete_request(self, unit_id):
        """Отправка DELETE-запроса на бэкенд"""
        # Обычно путь выглядит как /api/v1/unit_creator/{id}/, проверь под свой бэкенд
        url_path = f"/api/v1/unit_creator/{unit_id}/"
        try:
            response = await self.client.delete(url_path)
            if response.status_code in (200, 204): # 204 No Content часто используется для DELETE
                await self.update_data() # Обновляем таблицу после успешного удаления
            else:
                print(f"Ошибка бэкенда при удалении: {response.status_code}")
        except Exception as e:
            print(f"Ошибка сети/запроса при удалении: {e}")

    def closeEvent(self, event):
        asyncio.ensure_future(self.client.aclose())
        event.accept()


class UsersTableWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Личный состав")
        self.all_persons = []
        self.selected_file_path = None  # Сюда сохраняем путь к выбранному фото
        self.resize(1200, 800) 
        
        self.client = httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=10.0)

        # правый layout
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0) 

        self.table = QTableWidget()
        self.table.setRowCount(0)
        # Увеличили до 5 колонок, чтобы добавить кнопки действий (Редактировать / Удалить)
        self.table.setColumnCount(5)
        
        headers = ['Id', 'ФИО', 'Фото', 'Отряд', 'Действия']
        self.table.setHorizontalHeaderLabels(headers)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) 
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.verticalHeader().setDefaultSectionSize(75)
        self.table.verticalHeader().setVisible(False)
        
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        right_layout.addWidget(self.table)

        # левый layout
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10) 

        # Кнопка закрытия
        close_button = QPushButton("Закрыть окно")
        close_button.setFixedWidth(120) 
        close_button.clicked.connect(self.close_this_window)
        
        left_layout.addWidget(close_button)
        left_layout.addStretch() 
        
        # Форма создания нового человека
        self.user_name_input = QLineEdit()
        self.user_name_input.setPlaceholderText("ФИО человека")
        self.user_name_input.setFixedWidth(150)

        self.user_image_input = QPushButton("Фото человека")
        self.user_image_input.setFixedWidth(150)
        self.user_image_input.clicked.connect(self.pick_file)

        self.user_unit_input = QLineEdit()
        self.user_unit_input.setPlaceholderText("ID отряда (число)")
        self.user_unit_input.setFixedWidth(150)

        create_button = QPushButton("Создать человека")
        create_button.setFixedWidth(150)
        create_button.clicked.connect(self.create_new_user)
        
        left_layout.addWidget(self.user_name_input)
        left_layout.addWidget(self.user_image_input)
        left_layout.addWidget(self.user_unit_input)
        left_layout.addWidget(create_button)
        left_layout.addSpacing(20) 

        # Главный контейнер
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15) 
        main_layout.setSpacing(15) 
        
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)

        self.setLayout(main_layout)
        
        # Автоматически загружаем данные при инициализации окна
        asyncio.ensure_future(self.update_data())

    def close_this_window(self):
        self.close()

    def pick_file(self):
        """Выбор файла фотографии через стандартный диалог"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите фото", "", "Изображения (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self.selected_file_path = file_path
            # Меняем текст кнопки на имя файла, чтобы пользователь видел, что файл выбран
            self.user_image_input.setText(os.path.basename(file_path))

    def create_new_user(self):
        """Слот создания: валидация полей и запуск асинхронного POST"""
        fio = self.user_name_input.text().strip()
        unit_id_str = self.user_unit_input.text().strip()
        
        if not fio or not unit_id_str or not self.selected_file_path:
            print("Заполните все поля и выберите фото!")
            return
            
        try:
            unit_id = int(unit_id_str)
        except ValueError:
            print("ID отряда должен быть числом")
            return

        asyncio.ensure_future(self.send_create_request(fio, unit_id, self.selected_file_path))

    async def send_create_request(self, fio, unit_id, file_path):
        """Отправка multipart/form-data на POST /prisoners"""
        url_path = "/prisoners"
        try:
            # Открываем файл и готовим данные для формы, как требует роут FastAPI (списки)
            with open(file_path, "rb") as f:
                files = [("files", (os.path.basename(file_path), f.read(), "image/jpeg"))]
                data = {
                    "fios": [fio],
                    "unit_id": [unit_id]
                }
                
                response = await self.client.post(url_path, files=files, data=data)
                
            if response.status_code in (200, 201):
                # Сбрасываем форму
                self.user_name_input.clear()
                self.user_unit_input.clear()
                self.user_image_input.setText("Фото человека")
                self.selected_file_path = None
                
                await self.update_data()
            else:
                print(f"Ошибка бэкенда при создании: {response.status_code}, {response.text}")
        except Exception as e:
            print(f"Ошибка сети при создании: {e}")

    async def update_data(self):
        """Получение списка всех заключенных/пользователей и рендер таблицы"""
        url_path = "/prisoners"
        try:
            response = await self.client.get(url_path)
            if response.status_code != 200:
                print(f"Не удалось загрузить данные: {response.status_code}")
                return
                
            result_data = response.json() # Напрямую получаем list[PrisonerGet]
            self.table.setRowCount(0)
            
            for i, prisoner in enumerate(result_data):
                self.table.insertRow(i)
                
                # Поля из PrisonerGet (подставьте точные ключи вашей модели, если они отличаются)
                p_id = prisoner.get('id')
                p_fio = prisoner.get('fio', 'Не указано')
                p_photo = prisoner.get('photo_url', '—') # или любой другой ключ ссылки на MinIO
                p_unit = prisoner.get('unit_id', '—')
                
                self.table.setItem(i, 0, QTableWidgetItem(str(p_id)))
                self.table.setItem(i, 1, QTableWidgetItem(str(p_fio)))
                self.table.setItem(i, 2, QTableWidgetItem(str(p_photo)))
                self.table.setItem(i, 3, QTableWidgetItem(str(p_unit)))
                
                # Контейнер для двух кнопок управления (Изменить и Удалить)
                actions_container = QWidget()
                actions_layout = QHBoxLayout(actions_container)
                actions_layout.setContentsMargins(5, 2, 5, 2)
                actions_layout.setSpacing(5)
                
                # Кнопка "Изменить"
                edit_btn = QPushButton("Изменить")
                edit_btn.clicked.connect(lambda checked, pid=p_id: self.edit_user(pid))
                
                # Кнопка "Удалить"
                delete_btn = QPushButton("Удалить")
                delete_btn.clicked.connect(lambda checked, pid=p_id: self.delete_user(pid))
                
                actions_layout.addWidget(edit_btn)
                actions_layout.addWidget(delete_btn)
                actions_container.setLayout(actions_layout)
                
                self.table.setCellWidget(i, 4, actions_container)
                
        except Exception as e:
            print(f"Ошибка при обновлении таблицы: {e}")

    def edit_user(self, prisoner_id):
        """Слот кнопки изменения: берет текущие данные из полей ввода и шлет PATCH"""
        fio = self.user_name_input.text().strip()
        unit_id_str = self.user_unit_input.text().strip()
        
        # Для PATCH сделаем валидацию: обновляем то, что заполнено в полях ввода
        payload = {}
        if fio:
            payload["fio"] = fio
        if unit_id_str:
            try:
                payload["unit_id"] = int(unit_id_str)
            except ValueError:
                print("Для изменения ID отряда должен быть числом")
                return
                
        if not payload:
            print("Введите новые ФИО или ID отряда в поля слева, чтобы изменить пользователя.")
            return
            
        asyncio.ensure_future(self.send_edit_request(prisoner_id, payload))

    async def send_edit_request(self, prisoner_id, payload):
        """Отправка PATCH JSON-запроса на бэкенд"""
        url_path = f"/prisoners/{prisoner_id}"
        try:
            # Передаем payload как JSON, соответствующий PrisonerUnitPatch
            response = await self.client.patch(url_path, json=payload)
            if response.status_code in (200, 204):
                self.user_name_input.clear()
                self.user_unit_input.clear()
                await self.update_data()
            else:
                print(f"Ошибка бэкенда при изменении: {response.status_code}")
        except Exception as e:
            print(f"Ошибка сети при изменении: {e}")

    def delete_user(self, prisoner_id):
        """Слот кнопки удаления: запускает асинхронный DELETE"""
        asyncio.ensure_future(self.send_delete_request(prisoner_id))

    async def send_delete_request(self, prisoner_id):
        """Отправка DELETE-запроса на бэкенд"""
        url_path = f"/prisoners/{prisoner_id}"
        try:
            response = await self.client.delete(url_path)
            if response.status_code in (200, 204):
                await self.update_data()
            else:
                print(f"Ошибка бэкенда при удалении: {response.status_code}")
        except Exception as e:
            print(f"Ошибка сети при удалении: {e}")

    def closeEvent(self, event):
        # Аккуратно закрываем сессию httpx при закрытии окна
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