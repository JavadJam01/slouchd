from PySide6.QtCore import Qt, QTimer, QRectF, Signal
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QProgressBar
from PySide6.QtGui import QGuiApplication, QPainter, QColor, QPen, QPainterPath

class CalibrationHUD(QWidget):
    """calibration progress hud"""
    WIDTH = 290
    HEIGHT = 52
    closed = Signal()

    def __init__(self, parent=None, is_window: bool = True):
        super().__init__(parent)
        self._is_window = is_window
        if is_window:
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Tool |
                Qt.WindowType.WindowDoesNotAcceptFocus
            )
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(self.WIDTH, self.HEIGHT)

        self._border_color = QColor("#3F3F46")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 9, 16, 10)
        layout.setSpacing(6)

        self.status_lbl = QLabel("calibrating...", self)
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet("color: #A1A1AA; font-size: 12px; font-weight: 600; font-family: 'Segoe UI', -apple-system, sans-serif;")
        layout.addWidget(self.status_lbl)

        self.bar = QProgressBar(self)
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setFixedHeight(6)
        self.bar.setTextVisible(False)
        self.bar.setStyleSheet("""
            QProgressBar {
                background-color: #27272A;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #10B981;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.bar)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._on_hide_timeout)

    def _on_hide_timeout(self):
        self.hide()
        self.closed.emit()

    def _reposition(self):
        if not self._is_window:
            return
        screen = QGuiApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            x = geom.x() + (geom.width() - self.WIDTH) // 2
            y = geom.y() + 14
            self.move(x, y)

    def show_progress(self, pct: int, msg: str = "calibrating..."):
        self._hide_timer.stop()
        self._border_color = QColor("#3F3F46")
        clean_msg = msg.lower()
        if "%" in clean_msg:
            import re
            clean_msg = re.sub(r'[\d\.]+\s*%', '', clean_msg).strip(" :")
        self.status_lbl.setText(clean_msg or "calibrating...")
        self.status_lbl.setStyleSheet("color: #A1A1AA; font-size: 12px; font-weight: 600; font-family: 'Segoe UI', -apple-system, sans-serif;")
        self.bar.setStyleSheet("""
            QProgressBar {
                background-color: #27272A;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #10B981;
                border-radius: 3px;
            }
        """)
        self.bar.setValue(pct)
        self._reposition()
        self.update()
        self.show()

    def show_done(self, msg: str = "posture calibrated"):
        self._border_color = QColor("#10B981")
        self.status_lbl.setText(msg.lower())
        self.status_lbl.setStyleSheet("color: #10B981; font-size: 12px; font-weight: 700; font-family: 'Segoe UI', -apple-system, sans-serif;")
        self.bar.setValue(100)
        self._reposition()
        self.update()
        self.show()
        self._hide_timer.start(1200)

    def show_error(self, err_msg: str):
        self._border_color = QColor("#EF4444")
        self.status_lbl.setText(err_msg.lower())
        self.status_lbl.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: 600; font-family: 'Segoe UI', -apple-system, sans-serif;")
        self.bar.setStyleSheet("""
            QProgressBar {
                background-color: #27272A;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #EF4444;
                border-radius: 3px;
            }
        """)
        self.bar.setValue(100)
        self._reposition()
        self.update()
        self.show()
        self._hide_timer.start(1600)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)

        painter.fillPath(path, QColor("#09090B"))
        painter.setPen(QPen(self._border_color, 1.5))
        painter.drawPath(path)
        painter.end()
