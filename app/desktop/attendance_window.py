import asyncio
import httpx
from PySide6.QtWidgets import (QLabel,
                             QVBoxLayout, QPushButton, QHBoxLayout, 
                             QWidget,QTableWidget,QTableWidgetItem,
                             QAbstractItemView,QHeaderView,QFrame)
from PySide6.QtGui import QPixmap, QColor, QBrush
from PySide6.QtCore import Qt


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
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(0, 200)
        
        self.table.verticalHeader().setDefaultSectionSize(75)
        self.table.verticalHeader().setVisible(False)
        
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        right_layout.addWidget(self.table)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)

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
            status_item = QTableWidgetItem(str(person.get("status") or "-"))
            self.table.setItem(i, 4, status_item)
            if status_item.text().lower() == "отсутствует":
                self.table.item(i, 4).setBackground(QColor("#FFCDD2"))
                self.table.item(i, 4).setForeground(QColor("#B71C1C"))

            # Загрузка фото
            cropped = person.get("cropped_photo")
            if isinstance(cropped, dict):
                url_cropped = f"{self.BASE_IMAGE_URL}{cropped.get('bucket')}/{cropped.get('path')}"
                asyncio.ensure_future(self.fetch_and_render_image(url_cropped, label_cropped))

            etalon = person.get("etalon_photo")
            if isinstance(etalon, dict):
                url_etalon = f"{self.BASE_IMAGE_URL}{etalon.get('bucket')}/{etalon.get('path')}"
                asyncio.ensure_future(self.fetch_and_render_image(url_etalon, label_etalon))

    async def fetch_and_render_image(self, url: str, target_label: QLabel):
        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                if not pixmap.isNull():
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