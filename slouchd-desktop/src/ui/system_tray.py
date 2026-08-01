from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import Signal

class SlouchdTrayIcon(QSystemTrayIcon):
    exit_requested = Signal()
    toggle_pause_requested = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_paused = False
        pix = QPixmap(32, 32)
        pix.fill(QColor(0, 0, 0, 0))
        p = QPainter(pix)
        p.setBrush(QColor("#10B981"))
        p.drawEllipse(4, 4, 24, 24)
        p.end()
        self.setIcon(QIcon(pix))
        self.setToolTip("slouchd — active")

        self.menu = QMenu()
        self.action_pause = self.menu.addAction("pause monitoring")
        self.action_pause.triggered.connect(self._toggle_pause)
        self.menu.addSeparator()
        self.action_exit = self.menu.addAction("quit slouchd")
        self.action_exit.triggered.connect(self.exit_requested.emit)
        self.setContextMenu(self.menu)

    def _toggle_pause(self):
        self.is_paused = not self.is_paused
        self.action_pause.setText("resume monitoring" if self.is_paused else "pause monitoring")
        self.toggle_pause_requested.emit(self.is_paused)
