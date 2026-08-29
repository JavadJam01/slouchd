from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QWidget
from PySide6.QtGui import QPainter, QColor

class TagPostureMeter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(592, 280)
        self.pitch = 0.0
        self.is_connected = False
        self.is_calibrated = False

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#18181B"))
        p.end()

class CalibrationDialog(QDialog):
    tag_calibrate_requested = Signal()
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.tag_meter = TagPostureMeter(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tag_meter)
        self.btn = QPushButton("calibrate baseline")
        layout.addWidget(self.btn)
        self.btn.clicked.connect(self.tag_calibrate_requested.emit)
