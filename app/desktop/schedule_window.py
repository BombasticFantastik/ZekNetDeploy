import sys
import asyncio
from datetime import datetime, timedelta

import httpx
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont, QCursor
from PySide6.QtWidgets import (
    QApplication, QWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QHBoxLayout, QPushButton, QHeaderView,
    QLabel, QComboBox, QDateEdit, QDialog,
    QTextEdit, QFormLayout, QFrame, QMenu, QLineEdit
)

STATUS_LIST = [
    ("PRESENT",       "П", "Присутствует",     "#E8F5E9", "#2E7D32"),
    ("BUSINESS_TRIP", "К", "Командировка",    "#E3F2FD", "#1565C0"),
    ("HOSPITAL",      "Б", "Болеет",          "#FFFDE7", "#F57F17"),
    ("VACATION",      "О", "Отпуск",          "#F3E5F5", "#7B1FA2"),
    ("DISCIPLINARY",  "Д", "Дисциплинарное",  "#FFEBEE", "#C62828"),
    ("OTHER",         "Р", "Рапорт / Другое", "#FFF3E0", "#E65100"),
]

STATUS_CONFIG = {s[0]: {"label": s[1], "name": s[2], "color": s[3], "text_color": s[4]} for s in STATUS_LIST}

_LEGACY_MAP = {"П": "PRESENT", "Б": "HOSPITAL", "Р": "OTHER", "Н": "DISCIPLINARY", "Командировка": "BUSINESS_TRIP"}

UNKNOWN_STATUS = {"label": "?", "name": "Неизвестно", "color": "#ECEFF1", "text_color": "#37474F"}


def _get_cfg(status: str) -> dict:
    canonical = _LEGACY_MAP.get(status, status)
    return STATUS_CONFIG.get(canonical, UNKNOWN_STATUS)


class ScheduleEditDialog(QDialog):
    def __init__(self, person_name, date_str, current_status, current_note, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Отметка: {person_name} ({date_str})")
        self.setFixedSize(380, 230)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.status_combo = QComboBox()
        for key, label, name, _, _ in STATUS_LIST:
            self.status_combo.addItem(f"{label} — {name}", key)
        canonical = _LEGACY_MAP.get(current_status, current_status)
        idx = self.status_combo.findData(canonical)
        if idx != -1:
            self.status_combo.setCurrentIndex(idx)

        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText("Заметка...")
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
        self.resize(1400, 800)

        self.client = httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=10.0)

        self.prisoners = []
        self.dates = []
        self.schedule_map = {}

        self._selected_schedule_id = None

        self.init_ui()
        asyncio.ensure_future(self.load_prisoners())
        asyncio.ensure_future(self.update_data())

    # ===================== UI =====================

    def init_ui(self):
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.currentCellChanged.connect(self.on_cell_selected)
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        left = QVBoxLayout()
        left.setSpacing(6)

        # --- Назад ---
        back_btn = QPushButton("Назад в меню")
        back_btn.clicked.connect(self.close)
        left.addWidget(back_btn)

        left.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        # --- Фильтр периода ---
        left.addWidget(QLabel("<b>Период отображения:</b>"))
        row1 = QHBoxLayout()
        self.filter_from = QDateEdit(QDate.currentDate().addDays(-6))
        self.filter_from.setCalendarPopup(True)
        self.filter_from.setMinimumDate(QDate(2020, 1, 1))
        self.filter_to = QDateEdit(QDate.currentDate())
        self.filter_to.setCalendarPopup(True)
        self.filter_to.setMinimumDate(QDate(2020, 1, 1))
        row1.addWidget(QLabel("С:"))
        row1.addWidget(self.filter_from)
        row1.addWidget(QLabel("По:"))
        row1.addWidget(self.filter_to)
        left.addLayout(row1)

        load_btn = QPushButton("Загрузить график")
        load_btn.clicked.connect(lambda: asyncio.ensure_future(self.update_data()))
        left.addWidget(load_btn)

        left.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        # --- CRUD форма ---
        left.addWidget(QLabel("<b>Управление записью:</b>"))

        self.form_prisoner = QComboBox()
        left.addWidget(QLabel("Заключённый:"))
        left.addWidget(self.form_prisoner)

        row2 = QHBoxLayout()
        self.form_date_from = QDateEdit()
        self.form_date_from.setCalendarPopup(True)
        self.form_date_from.setMinimumDate(QDate(2020, 1, 1))
        self.form_date_to = QDateEdit()
        self.form_date_to.setCalendarPopup(True)
        self.form_date_to.setMinimumDate(QDate(2020, 1, 1))
        row2.addWidget(QLabel("С:"))
        row2.addWidget(self.form_date_from)
        row2.addWidget(QLabel("По:"))
        row2.addWidget(self.form_date_to)
        left.addLayout(row2)

        self.form_status = QComboBox()
        for key, label, name, _, _ in STATUS_LIST:
            self.form_status.addItem(f"{label} — {name}", key)
        left.addWidget(QLabel("Статус:"))
        left.addWidget(self.form_status)

        self.form_note = QLineEdit()
        self.form_note.setPlaceholderText("Заметка (необязательно)")
        left.addWidget(QLabel("Заметка:"))
        left.addWidget(self.form_note)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(lambda: asyncio.ensure_future(self.save_schedule()))
        reset_btn = QPushButton("Сбросить на П")
        reset_btn.setStyleSheet("background-color: #FFCDD2; color: #B71C1C;")
        reset_btn.clicked.connect(lambda: asyncio.ensure_future(self.reset_to_present()))
        btn_row.addWidget(save_btn)
        btn_row.addWidget(reset_btn)
        left.addLayout(btn_row)

        self.form_info = QLabel("")
        left.addWidget(self.form_info)

        left.addStretch()

        # --- Легенда ---
        left.addWidget(QLabel("<b>Статусы:</b>"))
        for key, label, name, color, text_color in STATUS_LIST:
            lbl = QLabel(f"<b>{label}</b> — {name}")
            lbl.setStyleSheet(f"background-color: {color}; color: {text_color}; padding: 4px; border-radius: 4px;")
            left.addWidget(lbl)

        right = QVBoxLayout()
        right.addWidget(self.table)

        main = QHBoxLayout()
        main.addLayout(left, stretch=1)
        main.addLayout(right, stretch=4)
        self.setLayout(main)

    # ===================== ЗАГРУЗКА =====================

    async def load_prisoners(self):
        try:
            resp = await self.client.get("/api/v1/photoscan/prisoners")
            if resp.status_code == 200:
                self.prisoners = resp.json()
                self.form_prisoner.clear()
                for p in self.prisoners:
                    self.form_prisoner.addItem(p["fio"], p["id"])
        except Exception as e:
            print(f"Ошибка загрузки списка: {e}")

    async def update_data(self):
        date_from_str = self.filter_from.date().toString("yyyy-MM-dd")
        date_to_str = self.filter_to.date().toString("yyyy-MM-dd")

        start_dt = self.filter_from.date().toPython()
        end_dt = self.filter_to.date().toPython()

        self.dates = []
        curr = start_dt
        while curr <= end_dt:
            self.dates.append(curr.strftime("%Y-%m-%d"))
            curr += timedelta(days=1)

        try:
            resp = await self.client.get(
                "/api/v1/schedule/list",
                params={"date_from": date_from_str, "date_to": date_to_str}
            )
            if resp.status_code == 200:
                schedules = resp.json()
                self.schedule_map.clear()
                for item in schedules:
                    p_id = item.get("prisoner_id")
                    date_from = item.get("date_from")
                    date_to = item.get("date_to")
                    sid = item.get("id")
                    status = item.get("status", "PRESENT")
                    note = item.get("note", "")

                    if not date_from or not date_to:
                        continue

                    d = datetime.strptime(date_from, "%Y-%m-%d").date()
                    end = datetime.strptime(date_to, "%Y-%m-%d").date()
                    while d <= end:
                        self.schedule_map[(p_id, d.strftime("%Y-%m-%d"))] = {
                            "schedule_id": sid, "status": status, "note": note,
                            "date_from": date_from, "date_to": date_to
                        }
                        d += timedelta(days=1)

                self.render_table()
        except Exception as e:
            print(f"Ошибка загрузки: {e}")

    def render_table(self):
        self.table.clear()
        self.table.setRowCount(len(self.prisoners))
        self.table.setColumnCount(len(self.dates))

        headers = [datetime.strptime(d, "%Y-%m-%d").strftime("%d.%m") for d in self.dates]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setVerticalHeaderLabels([p["fio"] for p in self.prisoners])
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        for col in range(len(self.dates)):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

        font = QFont()
        font.setBold(True)

        for row, p in enumerate(self.prisoners):
            for col, dt in enumerate(self.dates):
                rec = self.schedule_map.get((p["id"], dt), {"status": "PRESENT", "note": ""})
                item = QTableWidgetItem(_get_cfg(rec["status"])["label"])
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFont(font)
                item.setData(Qt.ItemDataRole.UserRole, p["id"])
                item.setData(Qt.ItemDataRole.UserRole + 1, dt)
                self._apply_style(item, rec["status"], rec.get("note", ""))
                self.table.setItem(row, col, item)

    def _apply_style(self, item, status, note):
        cfg = _get_cfg(status)
        item.setText(cfg["label"])
        item.setBackground(QColor(cfg["color"]))
        item.setForeground(QColor(cfg["text_color"]))
        tip = f"Статус: {cfg['name']}"
        if note:
            tip += f"\n-------------------\nЗаметка: {note}"
        item.setData(Qt.ItemDataRole.ToolTipRole, tip)

    # ===================== ВЫБОР ЯЧЕЙКИ =====================

    def on_cell_selected(self, row, col, prev_row, prev_col):
        if row < 0 or col < 0 or not self.prisoners or col >= len(self.dates):
            return
        p_id = self.prisoners[row]["id"]
        dt = self.dates[col]
        rec = self.schedule_map.get((p_id, dt))

        if rec and rec.get("schedule_id"):
            self._selected_schedule_id = rec["schedule_id"]

            idx = self.form_prisoner.findData(p_id)
            if idx >= 0:
                self.form_prisoner.setCurrentIndex(idx)
            self.form_date_from.setDate(QDate.fromString(rec["date_from"], "yyyy-MM-dd"))
            self.form_date_to.setDate(QDate.fromString(rec["date_to"], "yyyy-MM-dd"))
            status_idx = self.form_status.findData(rec["status"])
            if status_idx >= 0:
                self.form_status.setCurrentIndex(status_idx)
            self.form_note.setText(rec.get("note", ""))
            self.form_info.setText(f"Диапазон #{rec['schedule_id']} выбран")
        else:
            self._selected_schedule_id = None

            idx = self.form_prisoner.findData(p_id)
            if idx >= 0:
                self.form_prisoner.setCurrentIndex(idx)
            self.form_date_from.setDate(QDate.fromString(dt, "yyyy-MM-dd"))
            self.form_date_to.setDate(QDate.fromString(dt, "yyyy-MM-dd"))
            self.form_status.setCurrentIndex(0)
            self.form_note.clear()
            self.form_info.setText("Новый диапазон (на день)")

    # ===================== CRUD =====================

    def _form_data(self):
        return {
            "prisoner_id": self.form_prisoner.currentData(),
            "date_from": self.form_date_from.date().toString("yyyy-MM-dd"),
            "date_to": self.form_date_to.date().toString("yyyy-MM-dd"),
            "status": self.form_status.currentData(),
            "note": self.form_note.text().strip()
        }

    def _clear_form(self):
        self._selected_schedule_id = None
        self.form_note.clear()
        self.form_status.setCurrentIndex(0)
        dt = QDate.currentDate()
        self.form_date_from.setDate(dt)
        self.form_date_to.setDate(dt)

    async def save_schedule(self):
        data = self._form_data()
        sid = self._selected_schedule_id
        try:
            if sid:
                payload = {k: v for k, v in data.items() if k != "prisoner_id"}
                resp = await self.client.patch(f"/api/v1/schedule/{sid}", json=payload)
            else:
                resp = await self.client.post("/api/v1/schedule/", json=data)

            if resp.status_code in (200, 201):
                res = resp.json()
                self._selected_schedule_id = res.get("id") if isinstance(res, dict) else None
                await self.update_data()
                self.form_info.setText("Сохранено")
                self._clear_form()
            else:
                print(f"Ошибка: {resp.status_code}")
                self.form_info.setText(f"Ошибка {resp.status_code}")
        except Exception as e:
            print(f"Ошибка сети: {e}")
            self.form_info.setText("Ошибка сети")

    async def reset_to_present(self):
        sid = self._selected_schedule_id
        if not sid:
            self.form_info.setText("Сначала выберите запись в таблице")
            return
        try:
            resp = await self.client.patch(f"/api/v1/schedule/{sid}", json={"status": "PRESENT", "note": ""})
            if resp.status_code == 200:
                self._selected_schedule_id = None
                await self.update_data()
                self.form_info.setText("Статус сброшен на Присутствует")
                self._clear_form()
            else:
                print(f"Ошибка: {resp.status_code}")
        except Exception as e:
            print(f"Ошибка сети: {e}")

    # ===================== ДИАЛОГ =====================

    def on_cell_double_clicked(self, row, col):
        item = self.table.item(row, col)
        if not item:
            return

        p_id = item.data(Qt.ItemDataRole.UserRole)
        dt = item.data(Qt.ItemDataRole.UserRole + 1)
        person_name = self.prisoners[row]["fio"]
        rec = self.schedule_map.get((p_id, dt), {"status": "PRESENT", "note": ""})

        dlg = ScheduleEditDialog(person_name, dt, rec["status"], rec.get("note", ""), self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_data = dlg.get_data()
            asyncio.ensure_future(self._save_cell(p_id, dt, new_data["status"], new_data["note"], item))

    async def _save_cell(self, p_id, dt, status, note, item):
        rec = self.schedule_map.get((p_id, dt))
        if rec and rec.get("schedule_id"):
            sid = rec["schedule_id"]
            resp = await self.client.patch(f"/api/v1/schedule/{sid}", json={"status": status, "note": note})
        else:
            resp = await self.client.post("/api/v1/schedule/", json={
                "prisoner_id": p_id, "date_from": dt, "date_to": dt,
                "status": status, "note": note
            })
        if resp.status_code in (200, 201):
            await self.update_data()
        else:
            print(f"Ошибка: {resp.status_code}")

    # ===================== КОНТЕКСТНОЕ МЕНЮ =====================

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return

        p_id = item.data(Qt.ItemDataRole.UserRole)
        dt = item.data(Qt.ItemDataRole.UserRole + 1)
        rec = self.schedule_map.get((p_id, dt))

        menu = QMenu(self)
        for key, label, name, _, _ in STATUS_LIST:
            action = menu.addAction(f"{label} — {name}")
            action.triggered.connect(lambda _, k=key: asyncio.ensure_future(
                self._save_cell(p_id, dt, k, rec.get("note", "") if rec else "", item)
            ))

        menu.addSeparator()

        if rec and rec.get("schedule_id"):
            del_action = menu.addAction(f"Удалить диапазон #{rec['schedule_id']}")
            del_action.triggered.connect(lambda: asyncio.ensure_future(self._delete_context(rec["schedule_id"])))

        menu.exec(QCursor.pos())

    async def _delete_context(self, sid):
        try:
            resp = await self.client.delete(f"/api/v1/schedule/{sid}")
            if resp.status_code == 200:
                await self.update_data()
        except Exception as e:
            print(f"Ошибка: {e}")

    # ===================== ЗАКРЫТИЕ =====================

    def closeEvent(self, event):
        event.accept()