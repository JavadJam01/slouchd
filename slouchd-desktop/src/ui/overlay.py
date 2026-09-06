import sys
from PySide6.QtCore import Qt, QRect, QPointF, Slot
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtGui import (
    QColor, QFont, QFontMetrics, QPainter, QGuiApplication,
    QRadialGradient, QBrush, QPixmap
)
from src.config import get_resource_path

class SlouchBanner(QWidget):
    """transparent S logo followed by LOUCH"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.font = QFont("Segoe UI", 88, QFont.Weight.Bold)
        self.font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 16)

        s_path = get_resource_path("assets/logo_s.png")
        if not s_path.exists():
            s_path = get_resource_path("assets/tray_icon.png")
        self._s_pixmap = QPixmap(str(s_path)) if s_path.exists() else None

        self.text = "LOUCH"
        self.sub_text = "ctrl+alt+c for recalibration"
        self.sub_font = QFont("Segoe UI", 16, QFont.Weight.DemiBold)
        self.sub_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        self._recalculate_size()

    def _recalculate_size(self):
        fm = QFontMetrics(self.font)
        sub_fm = QFontMetrics(self.sub_font)
        self.cap_height = fm.capHeight()
        self.text_width = fm.horizontalAdvance(self.text)
        self.sub_text_width = sub_fm.horizontalAdvance(self.sub_text)

        if self._s_pixmap and not self._s_pixmap.isNull():
            # scale logo height to font
            self.s_height = int(self.cap_height * 1.8)
            sw, sh = self._s_pixmap.width(), self._s_pixmap.height()
            self.s_width = int(self.s_height * (sw / sh)) if sh > 0 else int(self.s_height * 0.56)
            self.gap = 20
        else:
            self.s_height = 0
            self.s_width = 0
            self.gap = 0
            self.text = "SLOUCH"
            self.text_width = fm.horizontalAdvance(self.text)

        main_w = self.s_width + self.gap + self.text_width
        total_w = max(main_w, self.sub_text_width) + 24
        main_h = max(self.s_height, fm.height())
        self.sub_height = sub_fm.height()
        total_h = main_h + 12 + self.sub_height + 30
        self.setFixedSize(total_w, total_h)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        fm = QFontMetrics(self.font)
        main_h = max(self.s_height, fm.height())
        main_mid_y = 15 + main_h // 2
        baseline_y = main_mid_y + self.cap_height // 2
        color = QColor(239, 68, 68, 120)

        main_w = self.s_width + self.gap + self.text_width
        start_x = (self.width() - main_w) // 2

        if self._s_pixmap and not self._s_pixmap.isNull():
            # vertically center logo with text
            s_top = main_mid_y - self.s_height // 2
            scaled_s = self._s_pixmap.scaled(
                self.s_width, self.s_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            painter.setOpacity(110 / 255.0)
            painter.drawPixmap(start_x, s_top, scaled_s)
            text_x = start_x + self.s_width + self.gap
        else:
            text_x = start_x

        painter.setOpacity(1.0)
        painter.setFont(self.font)
        painter.setPen(color)
        painter.drawText(text_x, baseline_y, self.text)

        # recalibration hint text
        sub_y = 15 + main_h + 10
        sub_rect = QRect(0, sub_y, self.width(), self.sub_height)
        painter.setFont(self.sub_font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, self.sub_text)
        painter.end()

class MultiScreenDimmer(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self._is_dimmed = False
        self._huds = []

        self.setWindowFlags(	# clickthrough transparent overlay flags
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.banner = SlouchBanner(self)	# [S]louch! banner
        self.label = self.banner

        self.update_geometry()

        app = QGuiApplication.instance()	# handle screen changes
        if app:
            app.screenAdded.connect(self._on_screens_changed)
            app.screenRemoved.connect(self._on_screens_changed)
            for screen in QGuiApplication.screens():
                screen.geometryChanged.connect(self._on_screens_changed)

    def register_hud(self, hud):
        """register a hud widget to keep on top"""
        if hud and hud not in self._huds:
            self._huds.append(hud)

    def _keep_huds_on_top(self):
        """ensure registered huds stay above dimmer window"""
        for hud in self._huds:
            if hud and hud.isVisible():
                if hasattr(hud, "bring_to_front"):
                    hud.bring_to_front()
                else:
                    hud.raise_()
                if sys.platform == "win32":
                    try:
                        import ctypes
                        ctypes.windll.user32.SetWindowPos(int(self.winId()), int(hud.winId()), 0, 0, 0, 0, 0x0013)
                    except Exception:
                        pass

    @Slot()
    def _on_screens_changed(self, *args):
        self.update_geometry()

    def update_geometry(self):
        """cover all screens and center banner on primary display"""
        screens = QGuiApplication.screens()
        if not screens:
            return

        combined_rect = QRect()
        for screen in screens:
            combined_rect = combined_rect.united(screen.geometry())
        self.setGeometry(combined_rect)

        primary = QGuiApplication.primaryScreen() or screens[0]	# center banner on primary screen
        p_geom = primary.geometry()
        self.label.adjustSize()
        hint = self.label.size()
        rel_x = (p_geom.x() - combined_rect.x()) + (p_geom.width() - hint.width()) // 2
        rel_y = (p_geom.y() - combined_rect.y()) + (p_geom.height() - hint.height()) // 2
        self.label.move(rel_x, rel_y)

    def set_dimmed(self, dim: bool):
        if self._is_dimmed == dim:
            return

        self._is_dimmed = dim

        if dim:
            self.update_geometry()
            self.show()
            self.update()
            self._keep_huds_on_top()
        else:
            self.hide()

    def _draw_corner_glow(self, painter: QPainter, center_x: float, center_y: float, rect_x: int, rect_y: int, radius: int, glow_mult: float):
        """smooth red glow from a corner"""
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
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        opacity = float(self.config.get("dim_opacity", 0.65))
        opacity = max(0.0, min(1.0, opacity))
        alpha = int(255 * opacity)

        overlay_color = QColor(0, 0, 0, alpha)	# base dark dimming overlay
        painter.fillRect(self.rect(), overlay_color)

        glow_mult = max(0.35, opacity)	# draw ambient red glow at the corners of each connected display
        screens = QGuiApplication.screens()
        widget_pos = self.geometry().topLeft()

        for screen in screens:
            s_geom = screen.geometry()
            sx = s_geom.x() - widget_pos.x()
            sy = s_geom.y() - widget_pos.y()
            sw = s_geom.width()
            sh = s_geom.height()

            radius = max(240, int(min(sw, sh) * 0.42))

            self._draw_corner_glow(painter, sx, sy, sx, sy, radius, glow_mult)	# top-left corner
            self._draw_corner_glow(painter, sx + sw, sy, sx + sw - radius, sy, radius, glow_mult)	# top-right corner
            self._draw_corner_glow(painter, sx, sy + sh, sx, sy + sh - radius, radius, glow_mult)	# bottom-left corner
            self._draw_corner_glow(painter, sx + sw, sy + sh, sx + sw - radius, sy + sh - radius, radius, glow_mult)	# bottom-right corner
