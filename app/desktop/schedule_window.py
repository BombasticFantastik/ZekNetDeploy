import sys
import asyncio
from datetime import datetime, timedelta

import httpx
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont, QCursor
from PySide6.QtWidgets import (
    QApplication, QWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QHBoxLayout, QPushButton, QHeaderView,
    QMessageBox, QLabel, QComboBox, QDateEdit, QDialog,
    QTextEdit, QFormLayout, QFrame, QMenu
)

# --- Настройки статусов ---
STATUS_CONFIG = {
    "П": {"name": "Присутствует", "color": "#E8F5E9", "text_color": "#2E7D32"},
    "Б": {"name": "Болеет", "color": "#FFFDE7", "text_color": "#F57F17"},
    "Р": {"name": "Рапорт", "color": "#E3F2FD", "text_color": "#1565C0"},
    "Н": {"name": "Неизвестно", "color": "#FFEBEE", "text_color": "#C62828"},
}


class EditAttendanceDialog(QDialog):
    """Диалоговое окно редактирования записи"""
    def __init__(self, person_name: str, date_str: str, current_status: str, current_note: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Отметка: {person_name} ({date_str})")
        self.setFixedSize(380, 230)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.status_combo = QComboBox()
        for code, info in STATUS_CONFIG.items():
            self.status_combo.addItem(f"{code} — {info['name']}", code)
        
        index = self.status_combo.findData(current_status)
        if index != -1:
            self.status_combo.setCurrentIndex(index)

        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText("Введите текст заметки / рапорта (note)...")
        self.note_input.setPlainText(current_note or "")

        form_layout.addRow("Статус:", self.status_combo)
        form_layout.addRow("Заметка:", self.note_input)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def get_data(self):
        return {
            "status": self.status_combo.currentData(),
            "note": self.note_input.toPlainText().strip()
        }


class ScheduleTableWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("График и посещаемость")
        self.resize(1280, 750)

        self.client = httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=10.0)

        # Локальное состояние
        self.prisoners = []  # List[dict]: [{"id": 1, "name": "Иванов И."}]
        self.dates = []      # List[str]: ["2026-03-01", ...]
        
        # Маппинг: (prisoner_id, date_str) -> {"id": schedule_id, "status": "Б", "note": "..."}
        self.schedule_map = {}

        self.init_ui()

        # Первоначальная загрузка
        asyncio.ensure_future(self.update_data())

    def init_ui(self):
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        # --- Левая панель управления ---
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)

        close_button = QPushButton("Закрыть окно")
        close_button.clicked.connect(self.close)
        left_layout.addWidget(close_button)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        left_layout.addWidget(line)

        left_layout.addWidget(QLabel("<b>Период:</b>"))
        self.start_date_input = QDateEdit(QDate.currentDate().addDays(-6))
        self.start_date_input.setCalendarPopup(True)
        self.end_date_input = QDateEdit(QDate.currentDate())
        self.end_date_input.setCalendarPopup(True)

        left_layout.addWidget(QLabel("С:"))
        left_layout.addWidget(self.start_date_input)
        left_layout.addWidget(QLabel("По:"))
        left_layout.addWidget(self.end_date_input)

        fetch_btn = QPushButton("Загрузить график")
        fetch_btn.clicked.connect(lambda: asyncio.ensure_future(self.update_data()))
        left_layout.addWidget(fetch_btn)

        # Легенда
        left_layout.addWidget(QLabel("<b>Статусы:</b>"))
        for code, info in STATUS_CONFIG.items():
            lbl = QLabel(f"<b>{code}</b> — {info['name']}")
            lbl.setStyleSheet(f"background-color: {info['color']}; color: {info['text_color']}; padding: 4px; border-radius: 4px;")
            left_layout.addWidget(lbl)

        left_layout.addStretch()

        # --- Правая панель (Таблица) ---
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.table)

        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout, stretch=1)
        main_layout.addLayout(right_layout, stretch=4)
        self.setLayout(main_layout)

    # -------------------- HTTP ЗАПРОСЫ И ОТОБРАЖЕНИЕ --------------------

    async def update_data(self):
        """Загрузка списка записей с бэкенда"""
        date_from_str = self.start_date_input.date().toString("yyyy-MM-dd")
        date_to_str = self.end_date_input.date().toString("yyyy-MM-dd")

        # Формируем список дат для столбцов
        start_dt = self.start_date_input.date().toPython()
        end_dt = self.end_date_input.date().toPython()
        
        self.dates = []
        curr = start_dt
        while curr <= end_dt:
            self.dates.append(curr.strftime("%Y-%m-%d"))
            curr += timedelta(days=1)

        try:
            # 1. Загрузка списка человек (Замени при необходимости на свой эндпоинт)
            # response_p = await self.client.get("/api/v1/prisoners/")
            # self.prisoners = response_p.json()
            # self.prisoners = [
            #     {"id": 1, "name": "Алексеев Д."},
            #     {"id": 2, "name": "Борисов С."},
            #     {"id": 3, "name": "Васильев Е."}
            # ]
            response_p = await self.client.get("/api/v1/photoscan/prisoners")
            self.prisoners = response_p.json()
            print('_')
            print(self.prisoners)
            print('_')

            # 2. Вызов роутера GET /api/v1/schedule/list
            response = await self.client.get(
                "/api/v1/schedule/list",
                params={
                    "date_from": date_from_str,
                    "date_to": date_to_str
                }
            )

            if response.status_code == 200:
                schedules = response.json()
                self.schedule_map.clear()
                
                # Заполняем карту полученными с сервера объектами
                for item in schedules:
                    # Ожидается форма ответа: {"id": int, "prisoner_id": int, "date": "YYYY-MM-DD", "status": "...", "note": "..."}
                    p_id = item.get("prisoner_id")
                    dt = str(item.get("date"))
                    
                    self.schedule_map[(p_id, dt)] = {
                        "schedule_id": item.get("id"),
                        "status": item.get("status", "П"),
                        "note": item.get("note", "")
                    }

                self.render_table()
            else:
                print(f"Ошибка загрузки расписания: {response.status_code}")

        except Exception as e:
            print(f"Ошибка сети: {e}")

    def render_table(self):
        """Рендеринг QTableWidget"""
        self.table.clear()
        self.table.setRowCount(len(self.prisoners))
        self.table.setColumnCount(len(self.dates))

        # Заголовки
        headers = [datetime.strptime(d, "%Y-%m-%d").strftime("%d.%m") for d in self.dates]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setVerticalHeaderLabels([p["fio"] for p in self.prisoners])

        self.table.verticalHeader().setDefaultSectionSize(45)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        for col in range(len(self.dates)):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

        font = QFont()
        font.setBold(True)

        for row, p in enumerate(self.prisoners):
            for col, dt in enumerate(self.dates):
                record = self.schedule_map.get((p["id"], dt), {"status": "П", "note": ""})

                item = QTableWidgetItem(record["status"])
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFont(font)

                # Храним ID прямо в ячейке
                item.setData(Qt.ItemDataRole.UserRole, p["id"])
                item.setData(Qt.ItemDataRole.UserRole + 1, dt)

                self.apply_style(item, record["status"], record.get("note", ""))
                self.table.setItem(row, col, item)

    def apply_style(self, item: QTableWidgetItem, status: str, note: str):
        """Оформление ячейки и подсказки (ToolTip)"""
        cfg = STATUS_CONFIG.get(status, STATUS_CONFIG["П"])
        
        item.setText(status)
        item.setBackground(QColor(cfg["color"]))
        item.setForeground(QColor(cfg["text_color"]))

        tooltip = f"Статус: {cfg['name']}"
        if note:
            tooltip += f"\n-------------------\nЗаметка: {note}"
        
        item.setData(Qt.ItemDataRole.ToolTipRole, tooltip)

    # -------------------- ИЗМЕНЕНИЕ И PUT/DELETE --------------------

    def on_cell_double_clicked(self, row: int, col: int):
        item = self.table.item(row, col)
        if not item:
            return

        person_name = self.prisoners[row]["fio"]
        p_id = item.data(Qt.ItemDataRole.UserRole)
        dt = item.data(Qt.ItemDataRole.UserRole + 1)
        
        record = self.schedule_map.get((p_id, dt), {"status": "П", "note": ""})

        dialog = EditAttendanceDialog(
            person_name=person_name,
            date_str=dt,
            current_status=record["status"],
            current_note=record.get("note", ""),
            parent=self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_data = dialog.get_data()
            asyncio.ensure_future(self.save_schedule_change(p_id, dt, new_data["status"], new_data["note"], item))

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)
        for code, info in STATUS_CONFIG.items():
            action = menu.addAction(f"Поставить '{code}' ({info['name']})")
            action.triggered.connect(lambda _, c=code: self.quick_set_status(item, c))

        menu.exec(QCursor.pos())

    def quick_set_status(self, item: QTableWidgetItem, new_status: str):
        p_id = item.data(Qt.ItemDataRole.UserRole)
        dt = item.data(Qt.ItemDataRole.UserRole + 1)
        current_note = self.schedule_map.get((p_id, dt), {}).get("note", "")

        asyncio.ensure_future(self.save_schedule_change(p_id, dt, new_status, current_note, item))

    async def save_schedule_change(self, prisoner_id: int, date_str: str, status: str, note: str, item: QTableWidgetItem):
        """Отправка PUT /api/v1/schedule/ на бэкенд"""
        try:
            # Вызов @router.put("/")
            response = await self.client.put(
                "/api/v1/schedule/",
                json={
                    "prisoner_id": prisoner_id,
                    "date": date_str,
                    "status": status,
                    "note": note
                }
            )

            if response.status_code in (200, 201):
                res_data = response.json()
                
                # Обновляем локальную карту
                self.schedule_map[(prisoner_id, date_str)] = {
                    "schedule_id": res_data.get("id") if isinstance(res_data, dict) else None,
                    "status": status,
                    "note": note
                }
                
                # Обновляем визуальный стиль ячейки
                self.apply_style(item, status, note)
            else:
                print(f"Ошибка сохранения: {response.status_code}")
                QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить: {response.status_code}")

        except Exception as e:
            print(f"Ошибка сети PUT: {e}")

    def closeEvent(self, event):
        event.accept()
