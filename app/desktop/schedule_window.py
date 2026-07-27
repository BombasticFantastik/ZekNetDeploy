import asyncio
from datetime import datetime, timedelta

import httpx
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont, QCursor
from PySide6.QtWidgets import (
    QWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QHBoxLayout, QPushButton, QHeaderView,
    QLabel, QComboBox, QDateEdit,
    QFrame, QMenu, QLineEdit
)

STATUS_LIST = [
    ("NONE",          "—", "Нет статуса",     "#E8F5E9", "#2E7D32"),
    ("BUSINESS_TRIP", "К", "Командировка",    "#E3F2FD", "#1565C0"),
    ("HOSPITAL",      "Б", "Болеет",          "#FFFDE7", "#F57F17"),
    ("VACATION",      "О", "Отпуск",          "#F3E5F5", "#7B1FA2"),
    ("DISCIPLINARY",  "Д", "Дисциплинарное",  "#FFEBEE", "#C62828"),
    ("OTHER",         "Р", "Другое",          "#F5F5F5", "#616161"),
]

STATUS_CONFIG = {s[0]: {"label": s[1], "name": s[2], "color": s[3], "text_color": s[4]} for s in STATUS_LIST}

_LEGACY_MAP = {"П": "NONE", "Б": "HOSPITAL", "Р": "OTHER", "Н": "DISCIPLINARY", "Командировка": "BUSINESS_TRIP"}

UNKNOWN_STATUS = {"label": "?", "name": "Неизвестно", "color": "#ECEFF1", "text_color": "#37474F"}


def _get_cfg(status: str) -> dict:
    canonical = _LEGACY_MAP.get(status, status)
    return STATUS_CONFIG.get(canonical, UNKNOWN_STATUS)


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
        self._current_unit_id = None
        self._anchor_date = None
        self._anchor_prisoner_id = None

        self.init_ui()
        asyncio.ensure_future(self.load_units())

    # ===================== UI =====================

    def init_ui(self):
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.currentCellChanged.connect(self.on_cell_selected)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        left = QVBoxLayout()
        left.setSpacing(6)

        back_btn = QPushButton("Назад в меню")
        back_btn.clicked.connect(self.close)
        left.addWidget(back_btn)

        left.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        left.addWidget(QLabel("<b>Отряд:</b>"))
        self.unit_combo = QComboBox()
        self.unit_combo.currentIndexChanged.connect(self._on_unit_changed)
        left.addWidget(self.unit_combo)

        left.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

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
        reset_btn = QPushButton("Сбросить статус")
        reset_btn.setStyleSheet("background-color: #FFCDD2; color: #B71C1C;")
        reset_btn.clicked.connect(lambda: asyncio.ensure_future(self.reset_to_none()))
        btn_row.addWidget(save_btn)
        btn_row.addWidget(reset_btn)
        left.addLayout(btn_row)

        self.form_info = QLabel("")
        left.addWidget(self.form_info)

        left.addStretch()

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

    async def load_units(self):
        try:
            resp = await self.client.get("/api/v1/units/")
            if resp.status_code == 200:
                units = resp.json()
                self.unit_combo.blockSignals(True)
                self.unit_combo.clear()
                self.unit_combo.addItem("-- все отряды --", None)
                for u in units:
                    self.unit_combo.addItem(u["name"], u["id"])
                self.unit_combo.blockSignals(False)
                self._on_unit_changed(0)
        except Exception as e:
            print(f"Ошибка загрузки отрядов: {e}")

    def _on_unit_changed(self, index):
        self._current_unit_id = self.unit_combo.itemData(index)
        asyncio.ensure_future(self.load_prisoners())
        asyncio.ensure_future(self.update_data())

    async def load_prisoners(self):
        try:
            params = {}
            if self._current_unit_id is not None:
                params["unit_id"] = self._current_unit_id
            resp = await self.client.get("/api/v1/prisoners/", params=params)
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
                    status = item.get("status", "NONE")
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
                rec = self.schedule_map.get((p["id"], dt), {"status": "NONE", "note": ""})
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

    def _set_form_single_date(self, dt):
        qdt = QDate.fromString(dt, "yyyy-MM-dd")
        self.form_date_from.setDate(qdt)
        self.form_date_to.setDate(qdt)

    def on_cell_selected(self, row, col, prev_row, prev_col):
        if row < 0 or col < 0 or not self.prisoners or col >= len(self.dates):
            return
        p_id = self.prisoners[row]["id"]
        dt = self.dates[col]
        rec = self.schedule_map.get((p_id, dt))

        self._selected_schedule_id = None

        idx = self.form_prisoner.findData(p_id)
        if idx >= 0:
            self.form_prisoner.setCurrentIndex(idx)

        qdt = QDate.fromString(dt, "yyyy-MM-dd")

        if p_id == self._anchor_prisoner_id and self._anchor_date is not None and self._anchor_date != dt:
            d1 = QDate.fromString(self._anchor_date, "yyyy-MM-dd")
            d2 = QDate.fromString(dt, "yyyy-MM-dd")
            self.form_date_from.setDate(min(d1, d2))
            self.form_date_to.setDate(max(d1, d2))
            self._anchor_date = None
            self._anchor_prisoner_id = None
            self.form_info.setText(f"Диапазон с {self.form_date_from.date().toString('dd.MM')} по {self.form_date_to.date().toString('dd.MM')}")
        else:
            self._anchor_date = dt
            self._anchor_prisoner_id = p_id
            self._set_form_single_date(dt)
            self.form_info.setText(f"Запись на {qdt.toString('dd.MM.yyyy')} (кликните ещё одну ячейку для диапазона)")

        if rec and rec.get("schedule_id"):
            status_idx = self.form_status.findData(rec["status"])
            if status_idx >= 0:
                self.form_status.setCurrentIndex(status_idx)
            self.form_note.setText(rec.get("note", ""))
        else:
            self.form_status.setCurrentIndex(0)
            self.form_note.clear()

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

    async def save_schedule(self):
        data = self._form_data()
        is_single = data["date_from"] == data["date_to"]
        try:
            if is_single:
                resp = await self.client.post("/api/v1/schedule/", json=data)
                ok = resp.status_code == 201
            else:
                resp = await self.client.put("/api/v1/schedule/replace", json=data)
                ok = resp.status_code == 200
            if ok:
                await self.update_data()
                self.form_info.setText("Сохранено")
                self._clear_form()
            else:
                print(f"Ошибка: {resp.status_code} {resp.text[:200]}")
                self.form_info.setText(f"Ошибка {resp.status_code}")
        except Exception as e:
            print(f"Ошибка сети: {e}")
            self.form_info.setText("Ошибка сети")

    async def reset_to_none(self):
        row = self.table.currentRow()
        col = self.table.currentColumn()
        if row < 0 or col < 0 or not self.prisoners or col >= len(self.dates):
            self.form_info.setText("Выберите ячейку в таблице")
            return
        p_id = self.prisoners[row]["id"]
        dt = self.dates[col]
        rec = self.schedule_map.get((p_id, dt))
        sid = rec.get("schedule_id") if rec else None

        if sid is not None:
            try:
                resp = await self.client.delete(f"/api/v1/schedule/{sid}")
                if resp.status_code == 200:
                    await self.update_data()
                    self.form_info.setText("Статус сброшен")
                    self._clear_form()
                else:
                    print(f"Ошибка: {resp.status_code}")
            except Exception as e:
                print(f"Ошибка сети: {e}")
        else:
            self.form_info.setText("Нет записи для сброса")

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
            action.triggered.connect(lambda _, k=key, pid=p_id, d=dt: asyncio.ensure_future(
                self._context_set_status(pid, d, k)
            ))

        menu.addSeparator()

        if rec and rec.get("schedule_id"):
            del_action = menu.addAction(f"Удалить диапазон #{rec['schedule_id']}")
            del_action.triggered.connect(lambda s=rec["schedule_id"]: asyncio.ensure_future(self._delete_context(s)))

        menu.exec(QCursor.pos())

    async def _context_set_status(self, p_id, dt, status):
        try:
            json_data = {"prisoner_id": p_id, "date_from": dt, "date_to": dt, "status": status, "note": ""}
            resp = await self.client.post("/api/v1/schedule/", json=json_data)
            if resp.status_code == 201:
                await self.update_data()
        except Exception as e:
            print(f"Ошибка: {e}")

    async def _delete_context(self, sid):
        try:
            resp = await self.client.delete(f"/api/v1/schedule/{sid}")
            if resp.status_code == 200:
                await self.update_data()
        except Exception as e:
            print(f"Ошибка: {e}")

    # ===================== ЗАКРЫТИЕ =====================

    def showEvent(self, event):
        asyncio.ensure_future(self.load_units())
        super().showEvent(event)

    def closeEvent(self, event):
        event.accept()
