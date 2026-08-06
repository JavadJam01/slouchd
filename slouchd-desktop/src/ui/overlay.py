from PySide6.QtCore import Qt, QRect, QPointF, Slot
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QColor, QPainter, QGuiApplication, QRadialGradient, QBrush

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

    def _draw_corner_glow(self, painter: QPainter, center_x: float, center_y: float, rect_x: int, rect_y: int, radius: int, glow_mult: float):
        grad = QRadialGradient(QPointF(center_x, center_y), float(radius))
        grad.setColorAt(0.00, QColor(248, 113, 113, int(220 * glow_mult)))
        grad.setColorAt(0.12, QColor(239, 68, 68, int(190 * glow_mult)))
        grad.setColorAt(0.32, QColor(220, 38, 38, int(120 * glow_mult)))
        grad.setColorAt(0.58, QColor(185, 28, 28, int(55 * glow_mult)))
        grad.setColorAt(0.82, QColor(153, 27, 27, int(18 * glow_mult)))
        grad.setColorAt(1.00, QColor(127, 29, 29, 0))
        painter.fillRect(QRect(rect_x, rect_y, radius, radius), QBrush(grad))

    def paintEvent(self, event):
        if not self._is_dimmed:
            return
        painter = QPainter(self)
        opacity = float(self.config.get("dim_opacity", 0.65))
        alpha = int(255 * max(0.0, min(1.0, opacity)))
        painter.fillRect(self.rect(), QColor(0, 0, 0, alpha))

        glow_mult = max(0.35, opacity)
        screens = QGuiApplication.screens()
        widget_pos = self.geometry().topLeft()
        for screen in screens:
            s_geom = screen.geometry()
            sx = s_geom.x() - widget_pos.x()
            sy = s_geom.y() - widget_pos.y()
            sw = s_geom.width()
            sh = s_geom.height()
            radius = max(240, int(min(sw, sh) * 0.42))
            self._draw_corner_glow(painter, sx, sy, sx, sy, radius, glow_mult)
            self._draw_corner_glow(painter, sx + sw, sy, sx + sw - radius, sy, radius, glow_mult)
            self._draw_corner_glow(painter, sx, sy + sh, sx, sy + sh - radius, radius, glow_mult)
            self._draw_corner_glow(painter, sx + sw, sy + sh, sx + sw - radius, sy + sh - radius, radius, glow_mult)
        painter.end()
