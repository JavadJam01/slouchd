import sys
import signal
from PySide6.QtWidgets import QApplication
from src.config import ConfigManager
from src.camera.worker import CameraWorker
from src.ble.worker import BleTagWorker
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
        self.ble_worker = BleTagWorker(self.config)

        self.ble_worker.tag_connected.connect(self.on_tag_connected)
        self.ble_worker.tag_data.connect(self.on_tag_data)
        self.camera_worker.frame_ready.connect(self.on_camera_frame)
        self.tray.source_changed.connect(self.switch_perception_source)
        self.tray.exit_requested.connect(self.app.quit)

        self.camera_worker.start()
        self.ble_worker.start()
        self.apply_perception_source(self.config.get("perception_source", "camera"))
        self.tray.show()

    def apply_perception_source(self, source):
        self.dimmer.set_dimmed(False)
        if source == "tag":
            self.camera_worker.set_paused(True)
            self.ble_worker.set_paused(False)
        else:
            self.ble_worker.set_paused(True)
            self.camera_worker.set_paused(False)

    def switch_perception_source(self, source):
        self.config.set("perception_source", source)
        self.apply_perception_source(source)

    def on_tag_connected(self, conn, name):
        pass
    def on_tag_data(self, data):
        if self.config.get("perception_source") == "tag":
            self.dimmer.set_dimmed(data.get("is_slouching", False))
    def on_camera_frame(self, img, metrics, slouch, ratio):
        if self.config.get("perception_source") == "camera":
            self.dimmer.set_dimmed(slouch)

    def run(self):
        return self.app.exec()

def main():
    app = SlouchdApp()
    sys.exit(app.run())

if __name__ == "__main__":
    main()
