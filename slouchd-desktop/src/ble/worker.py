import asyncio
from PySide6.QtCore import QThread, Signal

class BleTagWorker(QThread):
    tag_connected = Signal(bool, str)
    tag_data = Signal(dict)
    tag_battery = Signal(int)
    tag_status = Signal(str)
    tag_error = Signal(str)

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self._running = True
        self._is_paused = False
        self._is_connected = False

    def run(self):
        print("ble worker running")

    def stop(self):
        self._running = False
