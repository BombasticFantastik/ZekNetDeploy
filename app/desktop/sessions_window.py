import asyncio
from datetime import datetime, date
import httpx
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QPushButton, QWidget,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QAbstractItemView, QDateEdit, QLabel)
from PySide6.QtCore import Qt, QDate
from app.desktop.attendance_window import AttendanceTableWindow


class SessionsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("История сессий")
        self.resize(1200, 800)

        self.client = httpx.AsyncClient(timeout=10.0)
        self.session_list = []

        left = QVBoxLayout()

        left.addWidget(QLabel("Выберите дату:"))
        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDate(QDate.currentDate())
        self.date_picker.dateChanged.connect(self._on_date_changed)
        left.addWidget(self.date_picker)

        self.session_table = QTableWidget()
        self.session_table.setColumnCount(3)
        self.session_table.setHorizontalHeaderLabels(["Дата", "Отряд", "Распознано"])
        h = self.session_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.session_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.session_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.session_table.cellClicked.connect(self._on_session_clicked)
        self.session_table.setMaximumWidth(350)
        left.addWidget(self.session_table)

        close_btn = QPushButton("Закрыть окно")
        close_btn.clicked.connect(self.close)
        left.addWidget(close_btn)

        self.report_window = AttendanceTableWindow()

        main = QHBoxLayout()
        main.addLayout(left, 0)
        main.addWidget(self.report_window, 1)

        self.setLayout(main)

    def showEvent(self, event):
        asyncio.ensure_future(self._load_sessions())
        super().showEvent(event)

    def _on_date_changed(self):
        asyncio.ensure_future(self._load_sessions())

    async def _load_sessions(self):
        qd = self.date_picker.date()
        d = date(qd.year(), qd.month(), qd.day())
        try:
            resp = await self.client.get(
                "http://127.0.0.1:8000/api/v1/photoscan/sessions",
                params={"date": d.isoformat()}
            )
            if resp.status_code != 200:
                return
            self.session_list = resp.json()
            self.session_table.setRowCount(0)
            for i, s in enumerate(self.session_list):
                self.session_table.insertRow(i)
                created = s.get("created_at", "")
                dt_str = created[:10] if created else "-"
                self.session_table.setItem(i, 0, QTableWidgetItem(dt_str))
                self.session_table.setItem(i, 1, QTableWidgetItem(str(s.get("unit_name", "-"))))
                self.session_table.setItem(i, 2, QTableWidgetItem(str(s.get("detected_count", 0))))
        except Exception as e:
            print(f"Ошибка загрузки сессий: {e}")

    def _on_session_clicked(self, row, col):
        if row < 0 or row >= len(self.session_list):
            return
        sid = self.session_list[row]["id"]
        asyncio.ensure_future(self._load_report(sid))

    async def _load_report(self, session_id: int):
        try:
            resp = await self.client.get(
                f"http://127.0.0.1:8000/api/v1/photoscan/sessions/{session_id}/report"
            )
            if resp.status_code == 200:
                data = resp.json()
                self.report_window.update_data(data)
        except Exception as e:
            print(f"Ошибка загрузки отчёта: {e}")
