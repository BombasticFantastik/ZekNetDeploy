import asyncio
import base64
import httpx
from PySide6.QtWidgets import (QLabel,
                             QVBoxLayout, QPushButton, QHBoxLayout,
                             QWidget, QTableWidget, QTableWidgetItem,
                             QAbstractItemView, QHeaderView, QFrame)
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtCore import Qt


class AttendanceTableWindow(QWidget):
    def __init__(self, show_back=True):
        super().__init__()
        self.setWindowTitle("Посещаемость — отчёт")
        self.all_persons = []
        self.resize(1200, 800)

        self.client = httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=10.0)

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setRowCount(0)
        self.table.setColumnCount(5)

        headers = ['ФИО', 'Лицо на фото', "Фото в базе", "Дистанция", "Статус"]
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

        if show_back:
            back_btn = QPushButton("Назад")
            back_btn.clicked.connect(self.close)
            left_layout.addWidget(back_btn)
            left_layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        left_layout.addWidget(QLabel("<b>Обозначения:</b>"))

        lbl_present_conflict = QLabel("■ В строю, но есть статус")
        lbl_present_conflict.setStyleSheet("background-color: #FFF9C4; color: #F57F17; padding: 6px; border-radius: 4px; font-weight: bold;")
        left_layout.addWidget(lbl_present_conflict)

        lbl_absent_ok = QLabel("■ Отсутствует (уваж. причина)")
        lbl_absent_ok.setStyleSheet("background-color: #F5F5F5; color: #616161; padding: 6px; border-radius: 4px; font-weight: bold;")
        left_layout.addWidget(lbl_absent_ok)

        lbl_absent_bad = QLabel("■ Отсутствует (без причины)")
        lbl_absent_bad.setStyleSheet("background-color: #FFCDD2; color: #B71C1C; padding: 6px; border-radius: 4px; font-weight: bold;")
        left_layout.addWidget(lbl_absent_bad)

        left_layout.addStretch()

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        main_layout.addLayout(left_layout, stretch=1)
        main_layout.addLayout(right_layout, stretch=5)

        self.setLayout(main_layout)

    def close_this_window(self):
        self.close()

    def update_data(self, result_data):
        self.all_persons = []

        def get_photo_path(photo):
            if isinstance(photo, dict):
                return photo.get("path")
            return photo

        cropped_photos = []

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

        self.table.setRowCount(0)
        image_requests = []

        for i, person in enumerate(self.all_persons):
            self.table.insertRow(i)

            self.table.setItem(i, 0, QTableWidgetItem(str(person.get("fio") or "Неизвестный")))

            label_cropped = QLabel("Нет фото")
            label_cropped.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(i, 1, label_cropped)

            label_etalon = QLabel("Нет фото")
            label_etalon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(i, 2, label_etalon)

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
            txt = status_item.text().lower()
            has_schedule = person.get("schedule_status") is not None
            if txt.startswith("присутствует") and has_schedule:
                self.table.item(i, 4).setBackground(QColor("#FFF9C4"))
                self.table.item(i, 4).setForeground(QColor("#F57F17"))
            elif txt == "отсутствует":
                self.table.item(i, 4).setBackground(QColor("#FFCDD2"))
                self.table.item(i, 4).setForeground(QColor("#B71C1C"))

            cropped = person.get("cropped_photo")
            if isinstance(cropped, dict):
                image_requests.append((label_cropped, cropped.get("bucket"), cropped.get("path")))

            etalon = person.get("etalon_photo")
            if isinstance(etalon, dict):
                image_requests.append((label_etalon, etalon.get("bucket"), etalon.get("path")))

        if image_requests:
            asyncio.ensure_future(self._load_batch_images(image_requests))

    async def _load_batch_images(self, requests: list[tuple[QLabel, str, str]]):
        payload = [{"bucket": b, "path": p} for _, b, p in requests]
        try:
            resp = await self.client.post("/api/v1/bucket_loader/images", json=payload)
            if resp.status_code != 200:
                return
            b64_list = resp.json()
            for (label, _, _), b64_data in zip(requests, b64_list):
                if b64_data is None:
                    continue
                try:
                    img_bytes = base64.b64decode(b64_data)
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_bytes)
                    if not pixmap.isNull():
                        scaled = pixmap.scaled(70, 70, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        label.setPixmap(scaled)
                except Exception:
                    pass
        except Exception as e:
            print(f"Ошибка загрузки фото: {e}")

    def closeEvent(self, event):
        event.accept()
