import sys
import asyncio
import httpx
from PySide6.QtWidgets import (QApplication)
import qasync  

#импорт main
from app.desktop.main_window import MainWindow


app = QApplication(sys.argv)

loop = qasync.QEventLoop(app)
asyncio.set_event_loop(loop)

window = MainWindow()
window.show()

with loop:
    loop.run_forever()