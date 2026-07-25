import asyncio
import httpx
from PySide6.QtWidgets import (QLabel, 
                             QVBoxLayout, QPushButton, QHBoxLayout, 
                             QWidget,QTableWidget,QTableWidgetItem,
                             QAbstractItemView,QHeaderView,QLineEdit,QFileDialog, QMessageBox)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

import os



class UnitsTableWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Отряды")
        self.resize(1200, 800)

        self.client = httpx.AsyncClient(
            base_url="http://127.0.0.1:8000",
            timeout=10.0
        )

        # таблица
        self.table = QTableWidget()
        self.table.setRowCount(0)
        self.table.setColumnCount(3)

        headers = ['Id', 'Название отряда', 'Действие']
        self.table.setHorizontalHeaderLabels(headers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        self.table.verticalHeader().setDefaultSectionSize(75)
        self.table.verticalHeader().setVisible(False)

        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        # левая панель
        left_layout = QVBoxLayout()

        close_button = QPushButton("Закрыть окно")
        close_button.clicked.connect(self.close)
        left_layout.addWidget(close_button)

        self.unit_name_input = QLineEdit()
        self.unit_name_input.setPlaceholderText("Имя нового отряда...")
        left_layout.addWidget(self.unit_name_input)

        create_button = QPushButton("Создать отряд")
        create_button.clicked.connect(self.create_new_unit)
        left_layout.addWidget(create_button)

        left_layout.addStretch()

        # правая панель
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.table)

        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)

        self.setLayout(main_layout)

        # ВАЖНО: загрузка данных при старте
        asyncio.ensure_future(self.update_data())

    # -------------------- CREATE --------------------

    def create_new_unit(self):
        name = self.unit_name_input.text().strip()

        if len(name) < 2:
            QMessageBox.warning(self, "Ошибка", "Слишком короткое имя")
            return

        self.unit_name_input.setDisabled(True)
        asyncio.ensure_future(self.send_create_request(name))

    async def send_create_request(self, name):
        try:
            response = await self.client.post(
                "/api/v1/units/",
                json={"name": name}
            )

            if response.status_code in (200, 201):
                self.unit_name_input.clear()
                await self.update_data()
            else:
                print(f"Ошибка создания: {response.status_code}")

        except Exception as e:
            print(f"Ошибка сети: {e}")

        finally:
            self.unit_name_input.setDisabled(False)

    # -------------------- GET --------------------

    async def update_data(self):
        try:
            response = await self.client.get("/api/v1/units/")

            if response.status_code != 200:
                print(f"GET ошибка: {response.status_code}")
                return

            result_data = response.json()

            if isinstance(result_data, list):
                units = result_data
            else:
                units = result_data.get("units", [])

            self.table.setRowCount(0)

            for i, unit in enumerate(units):
                self.table.insertRow(i)

                self.table.setItem(
                    i, 0,
                    QTableWidgetItem(str(unit.get("id")))
                )

                self.table.setItem(
                    i, 1,
                    QTableWidgetItem(unit.get("name", ""))
                )

                unit_id = unit.get("id")

                delete_button = QPushButton("Удалить")
                delete_button.clicked.connect(
                    lambda _, uid=unit_id: self.delete_unit(uid)
                )

                container = QWidget()
                layout = QHBoxLayout(container)
                layout.addWidget(delete_button)
                layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.setContentsMargins(5, 5, 5, 5)

                self.table.setCellWidget(i, 2, container)

        except Exception as e:
            print(f"Ошибка: {e}")

    # -------------------- DELETE --------------------

    def delete_unit(self, unit_id):
        asyncio.ensure_future(self.send_delete_request(unit_id))

    async def send_delete_request(self, unit_id):
        try:
            response = await self.client.delete(
                f"/api/v1/units/{unit_id}"
            )

            if response.status_code in (200, 204):
                await self.update_data()
            else:
                print(f"Ошибка удаления: {response.status_code}")

        except Exception as e:
            print(f"Ошибка сети: {e}")

    # -------------------- CLOSE --------------------

    def closeEvent(self, event):
        event.accept()


