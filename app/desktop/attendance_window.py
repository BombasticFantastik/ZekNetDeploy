import asyncio
import httpx
from PySide6.QtWidgets import (QLabel,
                             QVBoxLayout, QPushButton, QHBoxLayout, 
                             QWidget,QTableWidget,QTableWidgetItem,
                             QAbstractItemView,QHeaderView,QInputDialog,QFrame)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt


class AttendanceTableWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Присутствующие")
        self.all_persons = []
        self.resize(1200, 800) 
        self.selected_unit=1
        
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

        # --- ДОБАВЛЯЕМ ФИЛЬТР ---
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        left_layout.addWidget(line)

        filter_button = QPushButton("Выбрать Отряд")
        filter_button.setFixedWidth(150)
        filter_button.clicked.connect(self.select_and_filter_unit)
        left_layout.addWidget(filter_button)

        left_layout.addWidget(line)
        # ------------------------


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
        # 1. При получении новых данных с бэкенда очищаем текущий список,
        # чтобы данные прошлых отрядов не перемешивались
        self.all_persons = []

        def get_photo_path(photo):
            if isinstance(photo, dict):
                return photo.get("path")
            return photo

        cropped_photos = []

        # Наполняем список актуальными данными
        for person in result_data.get("expected_members", []):
            photo_path = get_photo_path(person.get("cropped_photo"))
            if photo_path is None or photo_path not in cropped_photos:
                person['unit'] = result_data.get('unit')
                self.all_persons.append(person)
                if photo_path:
                    cropped_photos.append(photo_path)

        for person in result_data.get("unexpected_members", []):
            photo_path = get_photo_path(person.get("cropped_photo"))
            if photo_path and photo_path not in cropped_photos:
                person['unit'] = result_data.get('unit')
                self.all_persons.append(person)
                cropped_photos.append(photo_path)

        # 2. Очищаем таблицу и перерисовываем
        self.table.setRowCount(0)

        for i, person in enumerate(self.all_persons):
            self.table.insertRow(i)

            self.table.setItem(i, 0, QTableWidgetItem(str(person.get("fio") or "Неизвестный")))

            label_cropped = QLabel("Нет фото")
            label_cropped.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(i, 1, label_cropped)

            label_etalon = QLabel("Нет фото")
            label_etalon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(i, 2, label_etalon)

            # Безопасное приведение distance
            distance = person.get("distance")
            if distance is None or distance == 'null':
                dist_str = "-"
            else:
                try:
                    dist_str = f"{float(distance):.4f}"
                except (ValueError, TypeError):
                    dist_str = "-"

            self.table.setItem(i, 3, QTableWidgetItem(dist_str))
            self.table.setItem(i, 4, QTableWidgetItem(str(person.get("status") or "-")))

            # Загрузка фото
            cropped = person.get("cropped_photo")
            if isinstance(cropped, dict):
                url_cropped = f"{self.BASE_IMAGE_URL}{cropped.get('bucket')}/{cropped.get('path')}"
                asyncio.ensure_future(self.fetch_and_render_image(url_cropped, label_cropped))

            etalon = person.get("etalon_photo")
            if isinstance(etalon, dict):
                url_etalon = f"{self.BASE_IMAGE_URL}{etalon.get('bucket')}/{etalon.get('path')}"
                asyncio.ensure_future(self.fetch_and_render_image(url_etalon, label_etalon))

        # 3. Применяем текущий фильтр к свеженарисованной таблице
        self.apply_unit_filter()

    async def show_unit_filter_dialog(self):
        """Загружает отряды и обновляет selected_unit"""
        try:
            response = await self.client.get("http://127.0.0.1:8000/api/v1/units/")
            if response.status_code != 200:
                print("Ошибка загрузки отрядов:", response.status_code)
                return

            units_data = response.json()
            if not units_data:
                print("Список отрядов пуст")
                return

            options = ["Все отряды"] + [f"{u.get('name', 'Без названия')} (ID: {u.get('id')})" for u in units_data]

            selected_option, ok = QInputDialog.getItem(
                self, "Выбор отряда", "Выберите отряд:", options, 0, False
            )

            if ok and selected_option:
                if selected_option == "Все отряды":
                    self.selected_unit = None
                else:
                    # Извлекаем ID как integer
                    target_unit_id = selected_option.split("(ID: ")[-1].replace(")", "").strip()
                    self.selected_unit = int(target_unit_id)

                # Вызываем фильтрацию элементов в таблице
                self.apply_unit_filter()

        except Exception as e:
            print("Ошибка при фильтрации по отряду:", repr(e))

    def apply_unit_filter(self):
        """Скрывает/показывает строки таблицы в соответствии с self.selected_unit"""
        if self.selected_unit is None:
            for i in range(self.table.rowCount()):
                self.table.setRowHidden(i, False)
            return

        for i, person in enumerate(self.all_persons):
            unit_data = person.get("unit")
            
            if isinstance(unit_data, dict):
                person_unit_id = unit_data.get("id")
            else:
                person_unit_id = person.get("unit_id") or unit_data

            # Сравниваем как строки, чтобы избежать ошибок с типом данных
            is_match = str(person_unit_id) == str(self.selected_unit)
            self.table.setRowHidden(i, not is_match)

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
            print("IMAGE LOAD ERROR:", url, repr(e))
            target_label.setText("Ошибка сети")

    def closeEvent(self, event):
        event.accept()

    def select_and_filter_unit(self):
            """Слот для кнопки фильтрации"""
            asyncio.ensure_future(self.show_unit_filter_dialog())

    async def show_unit_filter_dialog(self):
        """Загружает отряды и скрывает/показывает строки таблицы"""
        
        try:
            # Используем base_url бэкенда при вызове или полный адрес:
            response = await self.client.get("http://127.0.0.1:8000/api/v1/units/")
            if response.status_code != 200:
                print("Ошибка загрузки отрядов:", response.status_code)
                return

            units_data = response.json()
            if not units_data:
                print("Список отрядов пуст")
                return

            # Формируем список вариантов для выбора
            options = ["Все отряды"] + [f"{u.get('name', 'Без названия')} (ID: {u.get('id')})" for u in units_data]

            selected_option, ok = QInputDialog.getItem(
                self, 
                "Выбор отряда", 
                "Выберите отряд для фильтрации:", 
                options, 
                0, 
                False
            )
            #print(selected_option)

            if ok and selected_option:
                if selected_option == "Все отряды":
                    # Показываем абсолютно все строки
                    for i in range(self.table.rowCount()):
                        self.table.setRowHidden(i, False)
                else:
                    # Достаем ID отряда из скобок "ID: X"
                    target_unit_id = selected_option.split("(ID: ")[-1].replace(")", "").strip()
                    self.selected_unit=target_unit_id#SELECTED_UNIT

                    # Проверяем каждую запись из self.all_persons
                    for i, person in enumerate(self.all_persons):
                        # Извлекаем unit_id или unit -> id из объекта человека
                        unit_data = person.get("unit")
                        print(unit_data)
                        if isinstance(unit_data, dict):
                            person_unit_id = str(unit_data.get("id", ""))
                            person_unit_name = str(unit_data.get("name", ""))
                        else:
                            person_unit_id = str(person.get("unit_id") or unit_data or "")
                            person_unit_name = ""

                        # Совпадение по ID или имени отряда
                        is_match = (person_unit_id == target_unit_id) or (selected_option.split(" (ID:")[0] == person_unit_name)
                        
                        # Скрываем или отображаем соответствующую строку в таблице
                        self.table.setRowHidden(i, not is_match)

        except Exception as e:
            print("Ошибка при фильтрации по отряду:", repr(e))