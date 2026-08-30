from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QSlider, QPushButton
from PySide6.QtCore import Qt, Signal

class SettingsDialog(QDialog):
    settings_changed = Signal(dict)
    calibrate_requested = Signal()
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.setWindowTitle("slouchd settings")
        self.setFixedSize(520, 690)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("settings"))
        self.save_btn = QPushButton("save")
        layout.addWidget(self.save_btn)
    def set_tag_connected(self, c):
        pass
    def set_tag_battery(self, b):
        pass
    def set_tag_status_text(self, t, is_error=False):
        pass
    def set_source(self, s):
        pass
