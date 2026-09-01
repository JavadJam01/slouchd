import sys
import os
import time
import signal
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from src.config import ConfigManager, get_resource_path
from src.audio import play_audio_file
from src.camera.worker import CameraWorker
from src.ble.worker import BleTagWorker
from src.ui.overlay import MultiScreenDimmer
from src.ui.system_tray import SlouchdTrayIcon

class SlouchdApp:
    def __init__(self):
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("slouchd.desktop.app")
            except Exception:
                pass
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setApplicationName("slouchd")
        self.config = ConfigManager()
        self.dimmer = MultiScreenDimmer(self.config)
        self.tray = SlouchdTrayIcon()
        self.camera_worker = CameraWorker(self.config)
        self.ble_worker = BleTagWorker(self.config)
        self.tray.exit_requested.connect(self.app.quit)
        self.tray.show()
    def run(self):
        return self.app.exec()
def main():
    app = SlouchdApp()
    sys.exit(app.run())
if __name__ == "__main__":
    main()
