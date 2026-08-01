import sys
import signal
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from src.config import ConfigManager
from src.ui.system_tray import SlouchdTrayIcon

class SlouchdApp:
    def __init__(self):
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setApplicationName("slouchd")

        self.config = ConfigManager()
        self.tray = SlouchdTrayIcon()
        self.tray.exit_requested.connect(self.app.quit)
        self.tray.show()

    def run(self):
        return self.app.exec()

def main():
    app = SlouchdApp()
    sys.exit(app.run())

if __name__ == "__main__":
    main()
