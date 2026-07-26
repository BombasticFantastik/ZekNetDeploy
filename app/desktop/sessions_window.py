from PySide6.QtWidgets import (QVBoxLayout, QPushButton, QWidget,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QAbstractItemView)

class SessionsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("История сессий")
        self.resize(1000, 600)

        layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Отряд", "Дата", "Присутствовало"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        close_btn = QPushButton("Закрыть окно")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self.setLayout(layout)
