from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction, QActionGroup, QPainterPath

from src.config import get_resource_path

_TRAY_BASE_PIXMAP = None

def _get_base_tray_pixmap():
    global _TRAY_BASE_PIXMAP
    if _TRAY_BASE_PIXMAP is None:
        icon_path = get_resource_path("assets/logo_s.png")
        if not icon_path.exists():
            icon_path = get_resource_path("assets/tray_icon.png")
        if icon_path.exists():
            _TRAY_BASE_PIXMAP = QPixmap(str(icon_path))
    return _TRAY_BASE_PIXMAP

def create_tray_icon(bg_color_hex="#22C55E", s_color_hex="#6B111A"):
    """solid status badge with dark red S logo cutting through full height"""
    base_pix = _get_base_tray_pixmap()

    if base_pix is not None and not base_pix.isNull():
        icon = QIcon()
        for size in (16, 20, 24, 32, 48, 64):
            margin = 0.5 if size <= 20 else 1.0
            pixmap = QPixmap(size, size)
            pixmap.fill(QColor(0, 0, 0, 0))

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

            radius = max(2.0, (size - 2 * margin) * 0.24)
            path = QPainterPath()
            rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
            path.addRoundedRect(rect, radius, radius)

            # clip to squircle badge and fill with status background color
            painter.setClipPath(path)
            painter.fillPath(path, QColor(bg_color_hex))

            # scale S to full badge height
            h = int(round(size - 2 * margin))
            scaled_s = base_pix.scaledToHeight(h, Qt.TransformationMode.SmoothTransformation)
            w = scaled_s.width()
            x = (size - w) // 2

            # tint S to dark red
            s_pix = QPixmap(w, h)
            s_pix.fill(QColor(0, 0, 0, 0))
            sp = QPainter(s_pix)
            sp.setRenderHint(QPainter.RenderHint.Antialiasing)
            sp.drawPixmap(0, 0, scaled_s)
            sp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            sp.fillRect(s_pix.rect(), QColor(s_color_hex))
            sp.end()

            painter.drawPixmap(x, int(round(margin)), s_pix)
            painter.end()

            icon.addPixmap(pixmap)
        return icon

    # fallback to circle if asset is missing
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setBrush(QColor(0, 0, 0, 40))	# outer ring
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(6, 6, size - 12, size - 12)

    painter.setBrush(QColor(bg_color_hex))	# status dot
    painter.drawEllipse(10, 10, size - 20, size - 20)
    painter.end()

    return QIcon(pixmap)

_ICON_AMBER = None
_ICON_GREY = None
_ICON_RED = None
_ICON_GREEN = None
_ICON_BLUE = None

def _init_icons():
    global _ICON_AMBER, _ICON_GREY, _ICON_RED, _ICON_GREEN, _ICON_BLUE
    s_red = "#6B111A"  # signature dark red for the S logo
    if _ICON_AMBER is None:
        _ICON_AMBER = create_tray_icon("#F59E0B", s_red)
        _ICON_GREY = create_tray_icon("#9CA3AF", s_red)
        _ICON_RED = create_tray_icon("#F87171", s_red)   # lighter coral red for slouch status
        _ICON_GREEN = create_tray_icon("#22C55E", s_red)
        _ICON_BLUE = create_tray_icon("#38BDF8", s_red)

class SlouchdTrayIcon(QSystemTrayIcon):
    calibrate_requested = Signal()
    settings_requested = Signal()
    toggle_pause_requested = Signal(bool)
    source_changed = Signal(str)	# "tag" or "camera"
    exit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        _init_icons()
        self.is_paused = False
        self._current_state = None
        self.perception_source = "tag"
        self.tag_connected = False
        self.battery_pct = 100
        
        self._apply_state("UNCALIBRATED")

        self.menu = QMenu()	# context menu
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #1F1F23;
                background-color: #000000;
                color: #E4E4E7;
                border: 1px solid #27272A;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px 6px 12px;
                border-radius: 4px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: #2D1517;
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background-color: #27272A;
                margin: 4px 0px;
            }
            QMenu::indicator:checked {
                background-color: #DC2626;
                border-radius: 2px;
            }
            QMenu::right-arrow {
                image: none;
                border-top: 4px solid transparent;
                border-bottom: 4px solid transparent;
                border-left: 5px solid #A1A1AA;
                margin-right: 6px;
            }
            QMenu::right-arrow:selected {
                border-left-color: #EF4444;
            }
        """)

        self.action_calibrate = self.menu.addAction("calibrate")
        self.action_calibrate.triggered.connect(self.calibrate_requested.emit)

        self.source_menu = self.menu.addMenu("source")	# source switcher submenu
        self.source_group = QActionGroup(self)
        self.source_group.setExclusive(True)

        self.action_source_tag = QAction("wearable tag", self.source_menu, checkable=True)
        self.action_source_camera = QAction("webcam", self.source_menu, checkable=True)
        self.action_source_tag.setChecked(True)

        self.source_group.addAction(self.action_source_tag)
        self.source_group.addAction(self.action_source_camera)

        self.source_menu.addAction(self.action_source_tag)
        self.source_menu.addAction(self.action_source_camera)

        self.action_source_tag.triggered.connect(lambda: self.source_changed.emit("tag"))
        self.action_source_camera.triggered.connect(lambda: self.source_changed.emit("camera"))

        self.action_settings = self.menu.addAction("settings")
        self.action_settings.triggered.connect(self.settings_requested.emit)

        self.menu.addSeparator()

        self.action_pause = self.menu.addAction("pause monitoring")
        self.action_pause.triggered.connect(self._toggle_pause)

        self.menu.addSeparator()

        self.action_exit = self.menu.addAction("quit slouchd")
        self.action_exit.triggered.connect(self.exit_requested.emit)

        self.setContextMenu(self.menu)

    def set_source(self, source: str):
        self.perception_source = source
        if source == "tag":
            self.action_source_tag.setChecked(True)
            if not self.tag_connected:
                self._apply_state("NO_USER")
        else:
            self.action_source_camera.setChecked(True)
        self._refresh_tooltip()

    def set_tag_status(self, connected: bool, battery: int = -1):
        self.tag_connected = connected
        if battery >= 0:
            self.battery_pct = battery
        if self.perception_source == "tag" and not connected:
            self._apply_state("NO_USER")
        self._refresh_tooltip()

    def _refresh_tooltip(self):
        source_label = "tag" if self.perception_source == "tag" else "camera"
        if self.perception_source == "tag":
            conn_str = f"connected ({self.battery_pct}%)" if self.tag_connected else "searching for tag..."
            tag_info = f"[{source_label}: {conn_str}]"
        else:
            tag_info = f"[{source_label}]"

        if self.is_paused:
            state_str = "paused"
        elif self.perception_source == "tag" and not self.tag_connected:
            state_str = "searching for tag..."
        else:
            state_str = {
                "UNCALIBRATED": "need for calibration",
                "PAUSED": "paused",
                "NO_USER": "no user",
                "SLOUCHING": "slouching",
                "GOOD": "good posture"
            }.get(self._current_state, "ready")

        self.setToolTip(f"slouchd {tag_info} — {state_str}")

    def _apply_state(self, state: str):
        self._current_state = state
        if state == "UNCALIBRATED":
            self.setIcon(_ICON_AMBER)
        elif state == "PAUSED":
            self.setIcon(_ICON_AMBER)
        elif state == "NO_USER":
            self.setIcon(_ICON_GREY)
        elif state == "SLOUCHING":
            self.setIcon(_ICON_RED)
        elif state == "GOOD":
            self.setIcon(_ICON_GREEN)

        self._refresh_tooltip()

    def _toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.action_pause.setText("resume monitoring")
            self._apply_state("PAUSED")
        else:
            self.action_pause.setText("pause monitoring")
            self._current_state = None
            if self.perception_source == "tag":
                self.update_status(is_calibrated=True, is_slouching=False, user_present=self.tag_connected)
            else:
                self.update_status(is_calibrated=True, is_slouching=False, user_present=False)

        self.toggle_pause_requested.emit(self.is_paused)

    def update_status(self, is_calibrated: bool, is_slouching: bool, user_present: bool):
        if self.is_paused:
            return

        if self.perception_source == "tag" and not self.tag_connected:
            self._apply_state("NO_USER")
            return

        if not is_calibrated:
            self._apply_state("UNCALIBRATED")
        elif not user_present:
            self._apply_state("NO_USER")
        elif is_slouching:
            self._apply_state("SLOUCHING")
        else:
            self._apply_state("GOOD")
