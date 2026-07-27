import asyncio
import httpx
from PySide6.QtWidgets import (QLabel, 
                             QVBoxLayout, QPushButton, QHBoxLayout, 
                             QWidget,QTableWidget,QTableWidgetItem,
                             QAbstractItemView,QHeaderView,QLineEdit,QFileDialog,QFrame,QInputDialog)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt  
import os
from app.core.config import settings


class UsersTableWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Личный состав")
        self.all_persons = []
        self.selected_file_path = None  # Сюда сохраняем путь к выбранному фото
        self.current_selected_prisoner_id = None  # ID редактируемого записи
        self.resize(1200, 800) 

        self.BASE_IMAGE_URL = "http://127.0.0.1:8000/api/v1/bucket_loader/image/"
        self.client = httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=10.0)

        # Правый layout (Таблица)
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0) 

        self.table = QTableWidget()
        self.table.setRowCount(0)
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

        # Левый layout (Форма)
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10) 

        # Кнопка закрытия
        close_button = QPushButton("Закрыть окно")
        close_button.setFixedWidth(150) 
        close_button.clicked.connect(self.close_this_window)


        
        left_layout.addWidget(close_button)
        

        #фильтр
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        left_layout.addWidget(line)

        filter_button = QPushButton("Фильтровать по отряду")
        filter_button.clicked.connect(self.select_and_filter_unit)
        left_layout.addWidget(filter_button)


        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        left_layout.addWidget(line2)

        left_layout.addStretch() 


        
        # Форма создания / редактирования
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

        save_edit_button = QPushButton("Сохранить изм.")
        save_edit_button.setFixedWidth(150)
        save_edit_button.clicked.connect(self.save_edited_user)
        
        left_layout.addWidget(self.user_name_input)
        left_layout.addWidget(self.user_image_input)
        left_layout.addWidget(self.user_unit_input)
        left_layout.addWidget(create_button)
        left_layout.addWidget(save_edit_button)
        left_layout.addSpacing(20) 

        # Главный контейнер
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15) 
        main_layout.setSpacing(15) 
        
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)

        self.setLayout(main_layout)
        
        # Загрузка данных при старте
        asyncio.ensure_future(self.update_data())

    def close_this_window(self):
        self.close()

    def pick_file(self):
        """Быстрый выбор файла без зависания проводника"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Выберите фото", 
            "", 
            "Изображения (*.png *.jpg *.jpeg)",
            options=QFileDialog.Option.DontUseNativeDialog  # <-- Нативный диалог не фризит UI
        )
        if file_path:
            self.selected_file_path = file_path
            self.user_image_input.setText(os.path.basename(file_path))

    def create_new_user(self):
        """Валидация полей и запуск POST"""
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
        url_path = "/api/v1/prisoners/"

        try:
            # Асинхронно читаем файл в фоновом потоке, чтобы НЕ блокировать GUI поток PyQt
            def read_file():
                with open(file_path, "rb") as f:
                    return f.read()

            image_bytes = await asyncio.to_thread(read_file)

            files = {
                "files": (os.path.basename(file_path), image_bytes, "image/png")
            }

            data = {
                "fios": fio,
                "unit_id": str(unit_id)
            }

            response = await self.client.post(
                url_path,
                files=files,
                data=data
            )

            if response.status_code in (200, 201):
                self.user_name_input.clear()
                self.user_unit_input.clear()
                self.user_image_input.setText("Фото человека")
                self.selected_file_path = None

                await self.update_data()
            else:
                print(f"Ошибка бэкенда {response.status_code}: {response.text}")

        except Exception as e:
            print("Ошибка сети при создании:", repr(e))

    async def update_data(self):
        """Загрузка списка пользователей и рендер таблицы"""
        url_path = "/api/v1/prisoners/"
        try:
            response = await self.client.get(url_path)
            if response.status_code != 200:
                print(f"Не удалось загрузить данные: {response.status_code}")
                return
                
            result_data = response.json()
            self.table.setRowCount(0)
            
            for i, prisoner in enumerate(result_data):
                self.table.insertRow(i)
                
                p_id = prisoner.get("id")
                p_fio = prisoner.get("fio", "Не указано")
                
                # --- ПОЛУЧАЕМ ИЗОБРАЖЕНИЕ ---
                photo_obj = prisoner.get("photo_minio_path") or prisoner.get("photo")
                
                # Отряд
                unit = prisoner.get("unit")
                if isinstance(unit, dict):
                    p_unit_name = unit.get("name", "-")
                    raw_unit_id = unit.get("id", "")
                else:
                    raw_unit_id = prisoner.get("unit_id", "")
                    p_unit_name = str(raw_unit_id)
                
                # Заполнение базовых ячеек
                self.table.setItem(i, 0, QTableWidgetItem(str(p_id)))
                self.table.setItem(i, 1, QTableWidgetItem(str(p_fio)))
                
                # Ячейка с фото
                label_photo = QLabel("Нет фото")
                label_photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setCellWidget(i, 2, label_photo)

                # Обработка URL фото (если объект dict со строкой 'bucket' и 'path' или просто путь)
                if isinstance(photo_obj, dict):
                    bucket = photo_obj.get("bucket", settings.INFERENCE_BUCKET)
                    path = photo_obj.get("path", "")
                    img_url = f"{self.BASE_IMAGE_URL}{bucket}/{path}"
                    asyncio.ensure_future(self.fetch_and_render_image(img_url, label_photo))
                elif isinstance(photo_obj, str) and photo_obj and photo_obj != "—":
                    # Если бэкенд возвращает сразу имя файла (например uuid4.png)
                    # Подставь имя бакета, куда бэк сохраняет фото (например "photoscan" или "prisoners")
                    bucket = settings.INFERENCE_BUCKET
                    img_url = f"{self.BASE_IMAGE_URL}{bucket}/{photo_obj}"
                    asyncio.ensure_future(self.fetch_and_render_image(img_url, label_photo))

                self.table.setItem(i, 3, QTableWidgetItem(str(p_unit_name)))
                
                # Кнопки действий
                actions_container = QWidget()
                actions_layout = QHBoxLayout(actions_container)
                actions_layout.setContentsMargins(5, 2, 5, 2)
                actions_layout.setSpacing(5)
                
                edit_btn = QPushButton("Изменить")
                edit_btn.clicked.connect(
                    lambda checked, pid=p_id, fio=p_fio, uid=raw_unit_id: self.select_user_for_edit(pid, fio, uid)
                )
                
                delete_btn = QPushButton("Удалить")
                delete_btn.clicked.connect(
                    lambda checked, pid=p_id: self.delete_user(pid)
                )
                
                actions_layout.addWidget(edit_btn)
                actions_layout.addWidget(delete_btn)
                
                self.table.setCellWidget(i, 4, actions_container)
                
        except Exception as e:
            print(f"Ошибка при обновлении таблицы: {e}")

    async def fetch_and_render_image(self, url: str, target_label: QLabel):
        """Асинхронно скачивает картинку из MinIO и отображает её в QLabel"""
        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        70, 70, 
                        Qt.AspectRatioMode.KeepAspectRatio, 
                        Qt.TransformationMode.SmoothTransformation
                    )
                    target_label.setPixmap(scaled)
                else:
                    target_label.setText("Ошибка формата")
            else:
                target_label.setText(f"ошибка {response.status_code}")
        except Exception as e:
            print("IMAGE LOAD ERROR:", url, repr(e))
            target_label.setText("Ошибка сети")

    def select_user_for_edit(self, prisoner_id: int, fio: str, unit_id):
        """Подставляет данные пользователя в поля формы слева"""
        self.current_selected_prisoner_id = prisoner_id
        self.user_name_input.setText(str(fio) if fio != "Не указано" else "")
        self.user_unit_input.setText(str(unit_id) if unit_id is not None else "")

    def save_edited_user(self):
        """Отправка PATCH-запроса с изменениями"""
        if self.current_selected_prisoner_id is None:
            print("Ошибка: Сначала нажмите «Изменить» напротив нужного человека!")
            return

        fio = self.user_name_input.text().strip()
        unit_id_str = self.user_unit_input.text().strip()
        
        payload = {}
        if fio:
            payload["fio"] = fio

        if unit_id_str:
            try:
                payload["unit_id"] = int(unit_id_str)
            except ValueError:
                print("Ошибка: ID отряда должен быть числом")
                return
                
        if not payload:
            print("Заполните хотя бы одно поле перед сохранением!")
            return
            
        asyncio.ensure_future(self.send_edit_request(self.current_selected_prisoner_id, payload))

    async def send_edit_request(self, prisoner_id: int, payload: dict):
        url_path = f"/api/v1/prisoners/{prisoner_id}"
        try:
            response = await self.client.patch(url_path, json=payload)
            if response.status_code in (200, 204):
                self.user_name_input.clear()
                self.user_unit_input.clear()
                self.current_selected_prisoner_id = None
                await self.update_data()
            else:
                print(f"Ошибка бэкенда при изменении {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Ошибка сети при изменении: {repr(e)}")

    def delete_user(self, prisoner_id):
        asyncio.ensure_future(self.send_delete_request(prisoner_id))

    async def send_delete_request(self, prisoner_id):
        url_path = f"/api/v1/prisoners/{prisoner_id}"
        try:
            response = await self.client.delete(url_path)
            if response.status_code in (200, 204):
                await self.update_data()
            else:
                print(f"Ошибка бэкенда при удалении: {response.status_code}")
        except Exception as e:
            print(f"Ошибка сети при удалении: {e}")

    def closeEvent(self, event):
        event.accept()
    def select_and_filter_unit(self):
        """Слот, который вызывается по клику на кнопку фильтрации"""
        asyncio.ensure_future(self.show_unit_filter_dialog())

    async def show_unit_filter_dialog(self):
        try:
            # 1. Запрашиваем список отрядов
            response = await self.client.get("/api/v1/units/")
            if response.status_code != 200:
                print("Ошибка загрузки отрядов:", response.status_code)
                return

            units_data = response.json()  # Ожидаем список словарей, например: [{"id": 1, "name": "Отряд 1"}, ...]

            if not units_data:
                print("Список отрядов пуст")
                return

            # 2. Формируем список названий для выпадающего списка
            # Добавляем пункт "Все отряды" для сброса фильтра
            options = ["Все отряды"] + [f"{u.get('name', 'Без названия')} (ID: {u.get('id')})" for u in units_data]

            # 3. Показываем всплывающее диалоговое окно выбора
            selected_option, ok = QInputDialog.getItem(
                self, 
                "Выбор отряда", 
                "Выберите отряд для фильтрации:", 
                options, 
                0, 
                False
            )

            # 4. Если пользователь нажал "ОК"
            if ok and selected_option:
                if selected_option == "Все отряды":
                    # Показываем все строки в таблице
                    for i in range(self.table.rowCount()):
                        self.table.setRowHidden(i, False)
                else:
                    # Извлекаем ID из скобок (ID: X)
                    unit_id_str = selected_option.split("(ID: ")[-1].replace(")", "")
                    
                    # Фильтруем строки таблицы по названию или ID отряда (Колонка 3 - "Отряд")
                    for i in range(self.table.rowCount()):
                        unit_item = self.table.item(i, 3)
                        unit_text = unit_item.text() if unit_item else ""
                        
                        # Скрываем строку, если ID или Название не совпадают с выбранным
                        is_match = (unit_id_str == unit_text) or (selected_option.split(" (ID:")[0] in unit_text)
                        self.table.setRowHidden(i, not is_match)

        except Exception as e:
            print("Ошибка при фильтрации по отряду:", repr(e))