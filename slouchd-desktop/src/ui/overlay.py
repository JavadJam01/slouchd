from PySide6.QtCore import Qt, QRect, Slot
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QColor, QPainter, QGuiApplication

class MultiScreenDimmer(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self._is_dimmed = False

        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.update_geometry()

    def update_geometry(self):
        screens = QGuiApplication.screens()
        if not screens:
            return
        combined_rect = QRect()
        for screen in screens:
            combined_rect = combined_rect.united(screen.geometry())
        self.setGeometry(combined_rect)

    def set_dimmed(self, dim: bool):
        if self._is_dimmed == dim:
            return
        self._is_dimmed = dim
        if dim:
            self.update_geometry()
            self.show()
            self.update()
        else:
            self.hide()

    def paintEvent(self, event):
        if not self._is_dimmed:
            return
        painter = QPainter(self)
        opacity = float(self.config.get("dim_opacity", 0.65))
        alpha = int(255 * max(0.0, min(1.0, opacity)))
        painter.fillRect(self.rect(), QColor(0, 0, 0, alpha))
        painter.end()
