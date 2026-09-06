import sys
from PySide6.QtCore import Qt, Signal, QRectF, QPoint, QTimer
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QWidgetAction, QLabel, QWidget, QHBoxLayout
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction, QActionGroup, QPainterPath, QCursor, QGuiApplication, QFont

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

def draw_battery_icon(pct: int, w: int = 22, h: int = 11) -> QPixmap:
    scale = 2
    pix = QPixmap(w * scale, h * scale)
    pix.fill(Qt.GlobalColor.transparent)
    pix.setDevicePixelRatio(scale)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    if pct < 0:
        border_color = QColor("#3F3F46")
        bg_color = QColor("#141416")
    else:
        border_color = QColor("#71717A")
        bg_color = QColor("#18181B")

    if pct > 20:
        fill_color = QColor("#10B981")
    elif pct > 10:
        fill_color = QColor("#F59E0B")
    else:
        fill_color = QColor("#EF4444")

    body_w = w - 4.5
    body_h = h - 1.0
    body_path = QPainterPath()
    body_path.addRoundedRect(QRectF(0.5, 0.5, body_w, body_h), 2.5, 2.5)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.fillPath(body_path, bg_color)
    painter.strokePath(body_path, border_color)

    nip_w = 2.0
    nip_h = max(4.0, h * 0.44)
    nip_y = (h - nip_h) / 2.0
    nip_path = QPainterPath()
    nip_path.addRoundedRect(QRectF(w - 3.2, nip_y, nip_w, nip_h), 0.8, 0.8)
    painter.fillPath(nip_path, border_color)

    if pct >= 0:
        pct_clamped = max(0, min(100, pct))
        pad_x = 2.5
        pad_y = 2.5
        inner_w = body_w - (pad_x * 2)
        inner_h = body_h - (pad_y * 2)
        fill_w = max(2.0, inner_w * (pct_clamped / 100.0)) if pct_clamped > 0 else 0.0
        if fill_w > 0:
            fill_path = QPainterPath()
            fill_path.addRoundedRect(QRectF(pad_x + 0.5, pad_y + 0.5, fill_w, inner_h), 1.5, 1.5)
            painter.fillPath(fill_path, fill_color)

    painter.end()
    return pix

def promote_tray_icon_windows(target_exe_path: str | None = None) -> bool:
    """Ensures the slouchd system tray icon is promoted (always visible on taskbar) on Windows 10/11.

    Finds the app's entry in HKCU\\Control Panel\\NotifyIconSettings and sets 'IsPromoted' to 1.
    Windows Explorer detects this change immediately without requiring an explorer restart.
    """
    if sys.platform != "win32":
        return False

    try:
        import winreg
        from pathlib import Path

        if target_exe_path:
            current_exe = str(Path(target_exe_path).resolve()).replace("/", "\\").lower()
        else:
            current_exe = str(Path(sys.executable).resolve()).replace("/", "\\").lower()

        target_names = ["slouchd.exe"]
        if not getattr(sys, "frozen", False):
            target_names.append(Path(sys.executable).name.lower())

        reg_path = r"Control Panel\NotifyIconSettings"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ) as root_key:
            num_subkeys, _, _ = winreg.QueryInfoKey(root_key)
            promoted_any = False

            for i in range(num_subkeys):
                subkey_name = winreg.EnumKey(root_key, i)
                try:
                    with winreg.OpenKey(root_key, subkey_name, 0, winreg.KEY_READ) as subkey:
                        exe_path, _ = winreg.QueryValueEx(subkey, "ExecutablePath")
                        exe_path_norm = exe_path.strip().replace("/", "\\").lower()

                        is_match = (exe_path_norm == current_exe) or any(
                            exe_path_norm.endswith("\\" + name) for name in target_names
                        )

                        if not is_match:
                            continue

                        try:
                            is_promoted, _ = winreg.QueryValueEx(subkey, "IsPromoted")
                        except FileNotFoundError:
                            is_promoted = 0

                    if is_match and is_promoted != 1:
                        with winreg.OpenKey(root_key, subkey_name, 0, winreg.KEY_SET_VALUE) as subkey_write:
                            winreg.SetValueEx(subkey_write, "IsPromoted", 0, winreg.REG_DWORD, 1)
                        promoted_any = True
                    elif is_match and is_promoted == 1:
                        promoted_any = True
                except OSError:
                    continue

            return promoted_any
    except Exception:
        return False

class _TrayMenu(QMenu):
    """tray menu with shortcut label"""
    def __init__(self, tray_icon=None, parent=None):
        super().__init__(parent)
        self._tray_icon = tray_icon

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._tray_icon and hasattr(self._tray_icon, "action_calibrate"):
            p = QPainter(self)
            is_hovered = (self.activeAction() == self._tray_icon.action_calibrate)
            p.setPen(QColor("#A1A1AA") if is_hovered else QColor("#71717A"))
            p.setFont(QFont("Segoe UI", 9, QFont.Weight.Normal))
            r = self.actionGeometry(self._tray_icon.action_calibrate).adjusted(0, 0, -24, 0)
            p.drawText(r, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "ctrl+alt+c")
            p.end()



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
        self.battery_pct = -1
        self._tag_status_override = None
        self._tag_status_is_error = False
        self._promotion_scheduled = False
        
        self.menu = _TrayMenu(tray_icon=self)	# context menu
        self.menu.setObjectName("tray_menu")
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #000000;
                color: #E4E4E7;
                border: 1px solid #27272A;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu#tray_menu {
                min-width: 250px;
            }
            QMenu::item {
                padding: 10px 24px 10px 16px;
                border-radius: 5px;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 14px;
                margin: 1px 0px;
            }
            QMenu::item:selected {
                background-color: #2D1517;
                color: #FFFFFF;
            }
            QMenu::item:disabled {
                color: #71717A;
                background-color: #000000;
                padding: 8px 16px 4px 16px;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
            QMenu::separator {
                height: 1px;
                background-color: #27272A;
                margin: 6px 4px;
            }
            QMenu::indicator {
                width: 14px;
                height: 14px;
                margin-left: 6px;
            }
            QMenu::indicator:checked {
                background-color: #DC2626;
                border-radius: 2px;
            }
        """)

        self.header_widget = QWidget()
        self.header_widget.setStyleSheet("background-color: transparent;")
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(16, 8, 16, 4)
        header_layout.setSpacing(8)

        self.status_label = QLabel("starting...")
        self.status_label.setStyleSheet("color: #F59E0B; font-size: 13px; font-weight: 600;")
        header_layout.addWidget(self.status_label)

        header_layout.addStretch()

        self.bat_widget = QWidget()
        self.bat_widget.setStyleSheet("background-color: transparent;")
        bat_layout = QHBoxLayout(self.bat_widget)
        bat_layout.setContentsMargins(0, 0, 0, 0)
        bat_layout.setSpacing(5)

        self.bat_icon = QLabel()
        bat_layout.addWidget(self.bat_icon)

        self.bat_text = QLabel("")
        self.bat_text.setStyleSheet("color: #A1A1AA; font-size: 12px; font-weight: 500; font-family: 'Segoe UI', -apple-system, sans-serif;")
        bat_layout.addWidget(self.bat_text)

        header_layout.addWidget(self.bat_widget)
        self.bat_widget.setVisible(False)

        self.status_action = QWidgetAction(self.menu)
        self.status_action.setDefaultWidget(self.header_widget)
        self.menu.addAction(self.status_action)
        self.menu.addSeparator()

        self.action_calibrate = self.menu.addAction("calibrate")
        self.action_calibrate.triggered.connect(self.calibrate_requested.emit)

        self.source_menu = self.menu.addMenu("source")	# source switcher submenu
        self.source_menu.setObjectName("source_menu")
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

        self._apply_state("UNCALIBRATED")

        # open menu on click
        self.activated.connect(self._on_tray_activated)
        if sys.platform != "win32":
            self.setContextMenu(self.menu)

    def show(self):
        super().show()
        if sys.platform == "win32" and not self._promotion_scheduled:
            self._promotion_scheduled = True
            self._schedule_windows_promotion()

    def setVisible(self, visible: bool):
        super().setVisible(visible)
        if visible and sys.platform == "win32" and not self._promotion_scheduled:
            self._promotion_scheduled = True
            self._schedule_windows_promotion()

    def _schedule_windows_promotion(self, attempts_left: int = 3, delay_ms: int = 1000):
        if sys.platform != "win32":
            return

        def _attempt():
            success = promote_tray_icon_windows()
            if not success and attempts_left > 1:
                QTimer.singleShot(2000, lambda: self._schedule_windows_promotion(attempts_left - 1, 2000))

        QTimer.singleShot(delay_ms, _attempt)

    def _on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.Context,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_menu()

    def show_menu(self):
        if self.menu.isVisible():
            self.menu.close()
            return

        cursor_pos = QCursor.pos()
        screen = QGuiApplication.screenAt(cursor_pos) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()

        self.menu.adjustSize()
        hint = self.menu.sizeHint()
        menu_w = max(250, hint.width())
        menu_h = hint.height()

        # position above taskbar cursor
        target_x = cursor_pos.x() - menu_w // 2
        target_y = cursor_pos.y() - menu_h - 12

        # shift left if near bottom-right watermark
        watermark_zone_left = avail.right() - 320
        watermark_zone_top = avail.bottom() - 120

        if (target_x + menu_w > watermark_zone_left) and (cursor_pos.y() >= watermark_zone_top or target_y + menu_h > watermark_zone_top):
            target_x = watermark_zone_left - menu_w - 20

        # keep within screen bounds
        final_x = max(avail.left() + 12, min(target_x, avail.right() - menu_w - 12))
        final_y = max(avail.top() + 12, min(target_y, avail.bottom() - menu_h - 12))

        self.menu.popup(QPoint(int(final_x), int(final_y)))

    def set_source(self, source: str):
        self.perception_source = source
        if source == "tag":
            self.action_source_tag.setChecked(True)
            if not self.tag_connected:
                self._apply_state("NO_USER")
        else:
            self.action_source_camera.setChecked(True)
        self._refresh_tooltip()

    def set_tag_status_text(self, status: str, is_error: bool = False):
        self._tag_status_override = status.lower() if status else None
        self._tag_status_is_error = is_error
        self._refresh_tooltip()

    def set_tag_status(self, connected: bool, battery: int = -1):
        self.tag_connected = connected
        if battery >= 0:
            self.battery_pct = battery
        elif not connected:
            self.battery_pct = -1

        if connected:
            self._tag_status_override = None
            self._tag_status_is_error = False
        elif self.perception_source == "tag":
            self._apply_state("NO_USER")
        self._refresh_tooltip()

    def _refresh_tooltip(self):
        source_label = "tag" if self.perception_source == "tag" else "camera"

        if self.is_paused:
            status_str = "paused"
            status_color = "#F59E0B"
            tag_conn = f"connected ({self.battery_pct}%)" if (self.tag_connected and self.battery_pct >= 0) else ("connected" if self.tag_connected else "disconnected")
            tag_info = f"[{source_label}: {tag_conn}]" if self.perception_source == "tag" else f"[{source_label}]"
        elif self.perception_source == "tag" and not self.tag_connected:
            status_str = self._tag_status_override or "tag disconnected"
            if self._tag_status_is_error or any(k in status_str for k in ("off", "error", "unavailable", "failed")):
                status_color = "#EF4444"
            elif any(k in status_str for k in ("connecting", "scanning", "searching", "retrying")):
                status_color = "#F59E0B"
            else:
                status_color = "#71717A"
            tag_info = f"[{source_label}: {status_str}]"
        else:
            tag_conn = f"connected ({self.battery_pct}%)" if self.battery_pct >= 0 else "connected"
            tag_info = f"[{source_label}: {tag_conn}]" if self.perception_source == "tag" else f"[{source_label}]"
            state_map = {
                "UNCALIBRATED": ("need calibration", "#F59E0B"),
                "PAUSED": ("paused", "#F59E0B"),
                "NO_USER": ("no user", "#71717A"),
                "SLOUCHING": ("slouching alert", "#EF4444"),
                "GOOD": ("good posture", "#10B981")
            }
            status_str, status_color = state_map.get(self._current_state, ("ready", "#71717A"))

        self.setToolTip(f"slouchd {tag_info} — {status_str}")
        if hasattr(self, "status_label"):
            self.status_label.setText(status_str)
            self.status_label.setStyleSheet(
                f"color: {status_color}; font-size: 13px; font-weight: 600;"
            )

        # battery display logic
        if hasattr(self, "bat_widget"):
            if self.perception_source != "tag":
                # hide in webcam mode
                self.bat_widget.setVisible(False)
                self.action_source_tag.setText("wearable tag")
            elif self.tag_connected and self.battery_pct >= 0:
                self.bat_icon.setPixmap(draw_battery_icon(self.battery_pct, w=22, h=11))
                self.bat_text.setText(f"{self.battery_pct}%")
                self.bat_text.setVisible(True)
                if self.battery_pct <= 10:
                    self.bat_text.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: 600; font-family: 'Segoe UI', -apple-system, sans-serif;")
                elif self.battery_pct <= 20:
                    self.bat_text.setStyleSheet("color: #F59E0B; font-size: 12px; font-weight: 600; font-family: 'Segoe UI', -apple-system, sans-serif;")
                else:
                    self.bat_text.setStyleSheet("color: #A1A1AA; font-size: 12px; font-weight: 500; font-family: 'Segoe UI', -apple-system, sans-serif;")
                self.bat_widget.setToolTip(f"collar tag battery: {self.battery_pct}%")
                self.bat_widget.setVisible(True)
                self.action_source_tag.setText(f"wearable tag ({self.battery_pct}%)")
            elif self.tag_connected:
                # waiting for battery reading
                self.bat_icon.setPixmap(draw_battery_icon(100, w=22, h=11))
                self.bat_text.setText("")
                self.bat_text.setVisible(False)
                self.bat_widget.setToolTip("collar tag connected (reading battery...)")
                self.bat_widget.setVisible(True)
                self.action_source_tag.setText("wearable tag")
            else:
                # dimmed shell when disconnected
                self.bat_icon.setPixmap(draw_battery_icon(-1, w=22, h=11))
                self.bat_text.setText("")
                self.bat_text.setVisible(False)
                self.bat_widget.setToolTip("collar tag disconnected")
                self.bat_widget.setVisible(True)
                self.action_source_tag.setText("wearable tag")

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
