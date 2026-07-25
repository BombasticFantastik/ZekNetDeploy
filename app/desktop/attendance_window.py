import asyncio
import httpx
from PySide6.QtWidgets import (QLabel,
                             QVBoxLayout, QPushButton, QHBoxLayout, 
                             QWidget,QTableWidget,QTableWidgetItem,
                             QAbstractItemView,QHeaderView)
from PySide6.QtGui import QPixmap
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

            # absent (нет фото) — добавляем всегда
            if photo_path is None:
                self.all_persons.append(person)
                continue

            if photo_path not in cropped_photos:
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
            print("IMAGE LOAD ERROR:", url, repr(e))
            target_label.setText("Ошибка сети")

    def closeEvent(self, event):
        event.accept()