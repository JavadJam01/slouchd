import sys
from PySide6.QtCore import Qt, Signal, QByteArray, QUrl, QRectF, QSize, QPoint
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, QScrollArea, QMenu
)
from PySide6.QtGui import QIcon, QPixmap, QPainter, QDesktopServices
from PySide6.QtSvg import QSvgRenderer
from src import __version__
from src.config import get_resource_path
from src.ui.calibration_dialog import CalibrationDialog
from src.ui.settings_dialog import SettingsDialog
from src.ui.system_tray import draw_battery_icon
from src.ui.updater import UpdateDialog

GITHUB_SVG = """<svg viewBox="0 0 16 16" width="20" height="20">
<path fill="{color}" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
</svg>"""

def _render_github_pixmap(color: str = "#71717A", size: int = 20) -> QPixmap:
    scale = 2
    renderer = QSvgRenderer(QByteArray(GITHUB_SVG.format(color=color).encode("utf-8")))
    pix = QPixmap(size * scale, size * scale)
    pix.fill(Qt.GlobalColor.transparent)
    pix.setDevicePixelRatio(scale)
    painter = QPainter(pix)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pix

class GitHubButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("view on github (JavadJam01/slouchd)")
        self.setFixedSize(24, 24)
        self.pix_normal = _render_github_pixmap("#71717A", 20)
        self.pix_hover = _render_github_pixmap("#FFFFFF", 20)
        self.setIcon(QIcon(self.pix_normal))
        self.setIconSize(self.pix_normal.size() / self.pix_normal.devicePixelRatio())
        self.setStyleSheet("background: transparent; border: none; padding: 0px;")
        self.clicked.connect(self._open_repo)

    def enterEvent(self, event):
        self.setIcon(QIcon(self.pix_hover))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setIcon(QIcon(self.pix_normal))
        super().leaveEvent(event)

    def _open_repo(self):
        QDesktopServices.openUrl(QUrl("https://github.com/JavadJam01/slouchd"))

KEBAB_SVG = """<svg viewBox="0 0 16 16" width="20" height="20">
<circle cx="8" cy="3" r="1.5" fill="{color}"/>
<circle cx="8" cy="8" r="1.5" fill="{color}"/>
<circle cx="8" cy="13" r="1.5" fill="{color}"/>
</svg>"""

def _render_kebab_pixmap(color: str = "#71717A", size: int = 20) -> QPixmap:
    scale = 2
    renderer = QSvgRenderer(QByteArray(KEBAB_SVG.format(color=color).encode("utf-8")))
    pix = QPixmap(size * scale, size * scale)
    pix.fill(Qt.GlobalColor.transparent)
    pix.setDevicePixelRatio(scale)
    painter = QPainter(pix)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pix

class MoreOptionsMenuButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("options & updates")
        self.setFixedSize(24, 24)
        self.pix_normal = _render_kebab_pixmap("#71717A", 20)
        self.pix_hover = _render_kebab_pixmap("#FFFFFF", 20)
        self.setIcon(QIcon(self.pix_normal))
        self.setIconSize(self.pix_normal.size() / self.pix_normal.devicePixelRatio())
        self.setStyleSheet("background: transparent; border: none; padding: 0px;")
        self._update_available = False
        self._latest_res = None
        self.clicked.connect(self._show_menu)

    def set_update_available(self, available: bool = True, latest_res: dict = None):
        self._update_available = available
        self._latest_res = latest_res
        color = "#22C55E" if available else "#71717A"
        self.pix_normal = _render_kebab_pixmap(color, 20)
        self.setIcon(QIcon(self.pix_normal))
        if available:
            self.setToolTip("update available! click for options")
        else:
            self.setToolTip("options & updates")

    def enterEvent(self, event):
        self.setIcon(QIcon(self.pix_hover))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setIcon(QIcon(self.pix_normal))
        super().leaveEvent(event)

    def _show_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #121216;
                color: #E4E4E7;
                border: 1px solid #27272A;
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 7px 16px;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background-color: #27272A;
                color: #FFFFFF;
            }
            QMenu::item:disabled {
                color: #A1A1AA;
                font-weight: 600;
                background-color: transparent;
                padding-bottom: 4px;
            }
            QMenu::separator {
                height: 1px;
                background: #27272A;
                margin: 4px 6px;
            }
        """)

        # current version info
        ver_action = menu.addAction(f"slouchd v{__version__}")
        ver_action.setEnabled(False)

        menu.addSeparator()

        # check for update option
        label = "update available!" if self._update_available else "check for updates..."
        update_action = menu.addAction(label)
        update_action.triggered.connect(lambda: self._open_update_dialog())

        releases_action = menu.addAction("release notes")
        releases_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/JavadJam01/slouchd/releases")))

        menu.exec(self.mapToGlobal(QPoint(0, self.height() + 4)))

    def _open_update_dialog(self, preloaded_result=None):
        res = preloaded_result or self._latest_res
        dlg = UpdateDialog(__version__, preloaded_result=res, parent=self.window())
        dlg.exec()

class CornerContainer(QWidget):
    # fixed width container to keep tabs centered
    def __init__(self, width: int = 110, height: int = 40, parent=None):
        super().__init__(parent)
        self._w = width
        self._h = height
        self.setFixedWidth(width)

    def sizeHint(self) -> QSize:
        return QSize(self._w, self._h)

    def minimumSizeHint(self) -> QSize:
        return QSize(self._w, self._h)

class SlouchdWindow(QWidget):
    camera_preview_needed = Signal(bool)
    settings_changed = Signal(dict)
    tag_calibrate_requested = Signal()

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.tag_connected = False
        self.tag_battery_pct = -1
        self.perception_source = self.config.get("perception_source", "tag")
        
        self.setWindowTitle("slouchd")
        icon_path = get_resource_path("assets/icon.png")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.setFixedSize(640, 660)
        self.setStyleSheet("""
            QWidget {
                background-color: #000000;
                color: #E4E4E7;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QTabWidget::pane {
                border-top: 1px solid #27272A;
                border-bottom: none;
                border-left: none;
                border-right: none;
                background-color: #000000;
            }
            QTabWidget::tab-bar {
                alignment: center;
            }
            QTabBar::tab {
                background: transparent;
                color: #71717A;
                font-size: 14px;
                font-weight: 600;
                padding: 12px 32px;
                border-bottom: 2px solid transparent;
            }
            QTabBar::tab:hover {
                color: #E4E4E7;
            }
            QTabBar::tab:selected {
                color: #FFFFFF;
                border-bottom: 2px solid #DC2626;
            }
            QScrollArea {
                border: none;
                background-color: #000000;
            }
            QScrollBar:vertical {
                background: #000000;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #27272A;
                min-height: 24px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #3F3F46;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget(self)

        # tab 1: calibrate
        self.calibration_page = CalibrationDialog(self.config, self)
        self.calibration_page.setWindowFlags(Qt.Widget)
        if hasattr(self.calibration_page, "btn_close"):
            self.calibration_page.btn_close.setVisible(False)
        self.calibration_page.tag_calibrate_requested.connect(self.tag_calibrate_requested.emit)
        self.tabs.addTab(self.calibration_page, "calibrate")

        # tab 2: settings
        self.settings_page = SettingsDialog(self.config, self)
        self.settings_page.setWindowFlags(Qt.Widget)
        if hasattr(self.settings_page, "btn_close"):
            self.settings_page.btn_close.setVisible(False)
        self.settings_page.settings_changed.connect(self.settings_changed.emit)
        # switch to calibrate tab
        self.settings_page.calibrate_requested.connect(lambda: self.show_tab("calibrate"))

        self.settings_scroll = QScrollArea(self)
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.settings_scroll.setStyleSheet("border: none; background-color: #000000;")
        self.settings_scroll.setWidget(self.settings_page)
        self.tabs.addTab(self.settings_scroll, "settings")

        # three-dot options menu and github button on top left
        self.left_container = CornerContainer(110, 40, self)
        self.left_container.setStyleSheet("background: transparent;")
        left_layout = QHBoxLayout(self.left_container)
        left_layout.setContentsMargins(20, 0, 0, 12)
        left_layout.setSpacing(10)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.options_btn = MoreOptionsMenuButton(self.left_container)
        self.github_btn = GitHubButton(self.left_container)
        left_layout.addWidget(self.options_btn)
        left_layout.addWidget(self.github_btn)
        self.tabs.setCornerWidget(self.left_container, Qt.Corner.TopLeftCorner)

        # battery indicator on top right
        self.right_container = CornerContainer(110, 40, self)
        self.right_container.setStyleSheet("background: transparent;")
        right_layout = QHBoxLayout(self.right_container)
        right_layout.setContentsMargins(0, 0, 24, 12)
        right_layout.setSpacing(7)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.bat_icon = QLabel(self.right_container)
        self.bat_icon.setStyleSheet("background: transparent;")

        self.bat_text = QLabel(self.right_container)
        self.bat_text.setStyleSheet(
            "color: #A1A1AA; font-size: 13px; font-weight: 600; font-family: 'Segoe UI', -apple-system, sans-serif; background: transparent;"
        )

        right_layout.addWidget(self.bat_icon)
        right_layout.addWidget(self.bat_text)
        self.tabs.setCornerWidget(self.right_container, Qt.Corner.TopRightCorner)
        self._update_battery_ui()

        layout.addWidget(self.tabs)

        self.tabs.currentChanged.connect(self._on_tab_changed)

    def show_tab(self, tab_name: str = "calibrate"):
        if tab_name.lower() in ("calibrate", "calibration", "posture"):
            self.tabs.setCurrentIndex(0)
        else:
            self.tabs.setCurrentIndex(1)
        self.show()
        self.raise_()
        self.activateWindow()

    def open_update_dialog(self, preloaded_result: dict = None):
        self.show()
        self.raise_()
        self.activateWindow()
        self.options_btn._open_update_dialog(preloaded_result=preloaded_result)

    def _on_tab_changed(self, index: int):
        is_calibrate = (index == 0)
        is_camera = (self.config.get("perception_source", "tag") == "camera")
        self.camera_preview_needed.emit(is_calibrate and is_camera and self.isVisible())

    def closeEvent(self, event):
        self.camera_preview_needed.emit(False)
        super().closeEvent(event)

    def _update_battery_ui(self):
        # hide battery in webcam mode
        if self.perception_source != "tag":
            self.bat_icon.setVisible(False)
            self.bat_text.setVisible(False)
            self.right_container.setToolTip("")
            return

        self.bat_icon.setVisible(True)
        if self.tag_connected and self.tag_battery_pct >= 0:
            self.bat_icon.setPixmap(draw_battery_icon(self.tag_battery_pct, w=28, h=14))
            self.bat_text.setText(f"{self.tag_battery_pct}%")
            self.bat_text.setVisible(True)
            if self.tag_battery_pct <= 10:
                color = "#EF4444"
            elif self.tag_battery_pct <= 20:
                color = "#F59E0B"
            else:
                color = "#A1A1AA"
            self.bat_text.setStyleSheet(
                f"color: {color}; font-size: 13px; font-weight: 600; font-family: 'Segoe UI', -apple-system, sans-serif; background: transparent;"
            )
            self.right_container.setToolTip(f"collar tag battery: {self.tag_battery_pct}%")
        elif self.tag_connected:
            # connected but waiting for battery reading
            self.bat_icon.setPixmap(draw_battery_icon(100, w=28, h=14))
            self.bat_text.setText("")
            self.bat_text.setVisible(False)
            self.right_container.setToolTip("collar tag connected (reading battery...)")
        else:
            # dimmed shell when disconnected
            self.bat_icon.setPixmap(draw_battery_icon(-1, w=28, h=14))
            self.bat_text.setText("")
            self.bat_text.setVisible(False)
            self.right_container.setToolTip("collar tag disconnected")

    def set_source(self, source: str):
        self.perception_source = source
        self.calibration_page.set_source(source)
        self.settings_page.set_source(source)
        self._update_battery_ui()
        self._on_tab_changed(self.tabs.currentIndex())

    def set_tag_connected(self, connected: bool):
        self.tag_connected = bool(connected)
        if not connected:
            self.tag_battery_pct = -1
        self.settings_page.set_tag_connected(connected)
        if hasattr(self.calibration_page, "tag_meter"):
            if connected:
                self.calibration_page.tag_meter.is_connected = True
            else:
                self.calibration_page.tag_meter.set_disconnected()
        self._update_battery_ui()

    def set_tag_battery(self, battery_pct: int):
        self.tag_battery_pct = battery_pct
        self.settings_page.set_tag_battery(battery_pct)
        self.calibration_page.set_tag_battery(battery_pct)
        self._update_battery_ui()

    def set_tag_status_text(self, text: str, is_error: bool = False):
        self.settings_page.set_tag_status_text(text, is_error)
        self.calibration_page.set_tag_status_text(text, is_error)

    def update_tag_data(self, data: dict):
        if "battery" in data and data["battery"] >= 0 and self.tag_battery_pct < 0:
            self.set_tag_battery(data["battery"])
        if self.tabs.currentIndex() == 0 and self.isVisible():
            self.calibration_page.update_tag_data(data)

    def update_frame(self, qimg, metrics):
        if self.tabs.currentIndex() == 0 and self.isVisible():
            self.calibration_page.update_frame(qimg, metrics)

    def set_camera_error(self, err_msg: str):
        self.calibration_page.set_camera_error(err_msg)

