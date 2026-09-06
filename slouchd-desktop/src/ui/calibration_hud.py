import sys
from PySide6.QtCore import Qt, QTimer, QRectF, Signal, QSize
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QProgressBar
from PySide6.QtGui import QGuiApplication, QPainter, QColor, QPen, QPainterPath, QPixmap, QIcon

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

    def bring_to_front(self):
        """keep hud above overlay windows"""
        self.raise_()
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.SetWindowPos(int(self.winId()), 0, 0, 0, 0, 0, 0x0013)
            except Exception:
                pass

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
        self.bring_to_front()

    def show_done(self, msg: str = "posture calibrated"):
        self._border_color = QColor("#10B981")
        self.status_lbl.setText(msg.lower())
        self.status_lbl.setStyleSheet("color: #10B981; font-size: 12px; font-weight: 700; font-family: 'Segoe UI', -apple-system, sans-serif;")
        self.bar.setValue(100)
        self._reposition()
        self.update()
        self.show()
        self.bring_to_front()
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
        self.bring_to_front()
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


def _render_pause_icon(color: QColor, size: int = 14) -> QPixmap:
    scale = 2
    pix = QPixmap(size * scale, size * scale)
    pix.fill(Qt.GlobalColor.transparent)
    pix.setDevicePixelRatio(scale)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setBrush(color)
    p.setPen(Qt.PenStyle.NoPen)
    bar_w = 3.2
    bar_h = 10.0
    gap = 2.8
    x1 = (size - (2 * bar_w + gap)) / 2.0
    x2 = x1 + bar_w + gap
    y = (size - bar_h) / 2.0
    p.drawRoundedRect(QRectF(x1, y, bar_w, bar_h), 1.2, 1.2)
    p.drawRoundedRect(QRectF(x2, y, bar_w, bar_h), 1.2, 1.2)
    p.end()
    return pix


class PositionPromptHUD(QWidget):
    """hud prompt for posture recalibration and pause"""
    recalibrate_requested = Signal()
    pause_requested = Signal()
    WIDTH = 380
    HEIGHT = 54

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(self.WIDTH, self.HEIGHT)

        self._bg_color = QColor("#FACC15")
        self._border_color = QColor("#CA8A04")

        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.hide)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 8, 14, 8)
        layout.setSpacing(8)

        self.msg_lbl = QLabel("new sitting position?", self)
        self.msg_lbl.setStyleSheet("color: #18181B; font-size: 16px; font-weight: 700; font-family: 'Segoe UI', -apple-system, sans-serif;")
        layout.addWidget(self.msg_lbl, 1)

        self.btn_pause = QPushButton(self)
        self.btn_pause.setObjectName("btn_pause")
        self.btn_pause.setToolTip("pause monitoring")
        self.btn_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pause.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_pause.setFixedSize(34, 34)
        pause_pix = _render_pause_icon(QColor("#FAFAFA"), 14)
        self.btn_pause.setIcon(QIcon(pause_pix))
        self.btn_pause.setIconSize(QSize(14, 14))
        self.btn_pause.setStyleSheet("""
            QPushButton#btn_pause {
                background-color: #52525B;
                border: 1px solid #3F3F46;
                border-radius: 8px;
            }
            QPushButton#btn_pause:hover {
                background-color: #71717A;
                border: 1px solid #52525B;
            }
            QPushButton#btn_pause:pressed {
                background-color: #3F3F46;
                border: 1px solid #27272A;
            }
        """)
        self.btn_pause.clicked.connect(self._on_pause_clicked)
        layout.addWidget(self.btn_pause)

        self.btn_recalib = QPushButton("recalibrate", self)
        self.btn_recalib.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_recalib.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_recalib.setStyleSheet("""
            QPushButton {
                background-color: #18181B;
                color: #FAFAFA;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 14px;
                font-weight: 700;
                padding: 6px 16px;
                border: 1px solid #27272A;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #27272A;
                border: 1px solid #3F3F46;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #09090B;
                border: 1px solid #000000;
            }
        """)
        self.btn_recalib.clicked.connect(self._on_recalib_clicked)
        layout.addWidget(self.btn_recalib)

    def _on_pause_clicked(self):
        self.hide()
        self.pause_requested.emit()

    def _on_recalib_clicked(self):
        self.hide()
        self.recalibrate_requested.emit()

    def _reposition(self):
        screen = QGuiApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            x = geom.x() + (geom.width() - self.WIDTH) // 2
            y = geom.y() + 14
            self.move(x, y)

    def bring_to_front(self):
        """keep hud above overlay windows"""
        self.raise_()
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.SetWindowPos(int(self.winId()), 0, 0, 0, 0, 0, 0x0013)
            except Exception:
                pass

    def hide(self):
        if hasattr(self, "_auto_hide_timer"):
            self._auto_hide_timer.stop()
        super().hide()

    def show_prompt(self, message: str = "new sitting position?", theme: str = "yellow", auto_hide_ms: int = 0):
        if hasattr(self, "_auto_hide_timer"):
            self._auto_hide_timer.stop()
        self.msg_lbl.setText(message)
        if theme == "green":
            self._bg_color = QColor("#10B981")
            self._border_color = QColor("#059669")
        else:
            self._bg_color = QColor("#FACC15")
            self._border_color = QColor("#CA8A04")
        self._reposition()
        self.update()
        self.show()
        self.bring_to_front()
        if auto_hide_ms > 0 and hasattr(self, "_auto_hide_timer"):
            self._auto_hide_timer.start(auto_hide_ms)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 13, 13)

        painter.fillPath(path, self._bg_color)
        painter.setPen(QPen(self._border_color, 1.5))
        painter.drawPath(path)
        painter.end()
