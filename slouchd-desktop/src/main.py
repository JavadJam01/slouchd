import sys
import signal
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Slot
from src.config import ConfigManager
from src.camera.worker import CameraWorker
from src.ui.overlay import MultiScreenDimmer
from src.ui.system_tray import SlouchdTrayIcon

class SlouchdApp:
    def __init__(self):
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setApplicationName("slouchd")

        self.config = ConfigManager()
        self.dimmer = MultiScreenDimmer(self.config)
        self.tray = SlouchdTrayIcon()

        self.camera_worker = CameraWorker(self.config)
        self.camera_worker.frame_ready.connect(self.on_camera_frame)
        self.tray.exit_requested.connect(self.app.quit)

        self.tray.show()
        self.camera_worker.start()

    @Slot(object, dict, bool, float)
    def on_camera_frame(self, qimg, metrics, is_slouching, slouch_ratio):
        self.dimmer.set_dimmed(is_slouching)

    def run(self):
        return self.app.exec()

def main():
    app = SlouchdApp()
    sys.exit(app.run())

if __name__ == "__main__":
    main()
