from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QComboBox, QGroupBox, QCheckBox, QRadioButton,
    QButtonGroup, QWidget, QLineEdit, QListView
)
from PySide6.QtGui import QFont
import cv2
import os
from pathlib import Path
from src.config import get_resource_path, DEFAULT_CONFIG
from src.audio import play_audio_file

class SettingsDialog(QDialog):
    settings_changed = Signal(dict)
    calibrate_requested = Signal()

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self._is_tag_connected = False
        self._tag_status_override = None
        self._tag_status_is_error = False
        
        self.setWindowTitle("slouchd settings")
        self.setFixedSize(520, 690)
        self.setStyleSheet("""
            QDialog {
                background-color: #121216;
                background-color: #000000;
                color: #E4E4E7;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QLabel {
                color: #D1D5DB;
                font-size: 13px;
            }
            QLabel:disabled {
                color: #52525B;
            }
            QGroupBox {
                border: 1px solid #27272A;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 12px;
                font-weight: bold;
                color: #F4F4F5;
            }
            QGroupBox:disabled {
                color: #52525B;
                border-color: #202024;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #DC2626;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #EF4444;
            }
            QPushButton:disabled {
                background-color: #18181B;
                color: #52525B;
                border: 1px solid #27272A;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #27272A;
                border-radius: 3px;
            }
            QSlider::groove:horizontal:disabled {
                background: #18181B;
            }
            QSlider::sub-page:horizontal {
                background: #DC2626;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal:disabled {
                background: #27272A;
            }
            QSlider::handle:horizontal {
                background: #F4F4F5;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:disabled {
                background: #3F3F46;
            }
            QLineEdit {
                background-color: #18181B;
                color: #F4F4F5;
                border: 1px solid #27272A;
                border-radius: 6px;
                padding: 6px 12px;
                selection-background-color: #DC2626;
                selection-color: #FFFFFF;
            }
            QLineEdit:focus {
                border-color: #DC2626;
            }
            QLineEdit:disabled {
                background-color: #141416;
                color: #52525B;
                border-color: #202024;
            }
            QComboBox {
                background-color: #18181B;
                color: #F4F4F5;
                border: 1px solid #27272A;
                border-radius: 6px;
                padding: 6px 28px 6px 12px;
                selection-background-color: #2D1517;
                selection-color: #EF4444;
            }
            QComboBox:hover {
                border-color: #3F3F46;
            }
            QComboBox:focus, QComboBox:on {
                border-color: #DC2626;
            }
            QComboBox:disabled {
                background-color: #141416;
                color: #52525B;
                border-color: #202024;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 26px;
                border-left: 1px solid #27272A;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                background-color: #18181B;
            }
            QComboBox::drop-down:hover {
                background-color: #27272A;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #A1A1AA;
                margin-right: 2px;
            }
            QComboBox::down-arrow:on, QComboBox::down-arrow:hover {
                border-top-color: #EF4444;
            }
            QComboBox QAbstractItemView {
                background-color: #18181B;
                color: #F4F4F5;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                padding: 4px;
                selection-background-color: #2D1517;
                selection-color: #FFFFFF;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px 10px;
                border-radius: 4px;
                min-height: 22px;
            }
            QComboBox QAbstractItemView::item:selected,
            QComboBox QAbstractItemView::item:hover {
                background-color: #2D1517;
                color: #EF4444;
            }
            QRadioButton {
                color: #E4E4E7;
                font-size: 13px;
                spacing: 8px;
            }
            QRadioButton:disabled {
                color: #52525B;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 1px solid #3F3F46;
                background-color: #18181B;
            }
            QRadioButton::indicator:disabled {
                border-color: #27272A;
                background-color: #141416;
            }
            QRadioButton::indicator:checked {
                background-color: #DC2626;
                border-color: #DC2626;
            }
            QRadioButton::indicator:checked:disabled {
                background-color: #3F3F46;
                border-color: #3F3F46;
            }
            QCheckBox {
                color: #E4E4E7;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox:disabled {
                color: #52525B;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #3F3F46;
                background-color: #18181B;
            }
            QCheckBox::indicator:disabled {
                border-color: #27272A;
                background-color: #141416;
            }
            QCheckBox::indicator:checked {
                background-color: #DC2626;
                border-color: #DC2626;
            }
            QCheckBox::indicator:checked:disabled {
                background-color: #3F3F46;
                border-color: #3F3F46;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 12, 18, 16)

        src_group = QGroupBox("perception source", self)	# perception source selector group
        src_layout = QVBoxLayout(src_group)
        src_layout.setSpacing(8)

        cal_btn_style = """
            QPushButton {
                background-color: #27272A;
                color: #F4F4F5;
                font-size: 12px;
                font-weight: 600;
                padding: 4px 12px;
                border-radius: 6px;
                border: 1px solid #3F3F46;
            }
            QPushButton:hover {
                background-color: #2D1517;
                border-color: #DC2626;
                color: #FFFFFF;
            }
            QPushButton:disabled {
                background-color: #18181B;
                color: #52525B;
                border-color: #27272A;
            }
        """

        tag_row = QHBoxLayout()	# tag perception option
        self.radio_tag = QRadioButton("wearable tag (ble)", self)
        self.btn_cal_tag = QPushButton("calibrate", self)
        self.btn_cal_tag.setStyleSheet(cal_btn_style)
        self.btn_cal_tag.clicked.connect(self._calibrate_tag)
        tag_row.addWidget(self.radio_tag)
        tag_row.addStretch()
        tag_row.addWidget(self.btn_cal_tag)
        src_layout.addLayout(tag_row)

        cam_row = QHBoxLayout()	# webcam perception option
        self.radio_camera = QRadioButton("webcam (computer vision)", self)
        self.btn_cal_cam = QPushButton("calibrate", self)
        self.btn_cal_cam.setStyleSheet(cal_btn_style)
        self.btn_cal_cam.clicked.connect(self._calibrate_cam)
        cam_row.addWidget(self.radio_camera)
        cam_row.addStretch()
        cam_row.addWidget(self.btn_cal_cam)
        src_layout.addLayout(cam_row)

        self.source_btn_group = QButtonGroup(self)
        self.source_btn_group.addButton(self.radio_tag, 1)
        self.source_btn_group.addButton(self.radio_camera, 2)
        self.radio_tag.toggled.connect(self._on_source_toggled)
        self.radio_camera.toggled.connect(self._on_source_toggled)

        layout.addWidget(src_group)

        self.tag_group = QGroupBox("wearable tag settings", self)	# wearable tag settings
        tag_layout = QVBoxLayout(self.tag_group)

        tag_name_hdr = QHBoxLayout()	# tag device name (needed for finding)
        self.tag_name_lbl = QLabel("tag device name:", self)
        self.tag_name_input = QLineEdit(self)
        self.tag_name_input.setPlaceholderText("e.g. slouchd-tag")
        self.tag_name_input.setText(self.config.get("tag_name", "slouchd-tag"))
        tag_name_hdr.addWidget(self.tag_name_lbl)
        tag_name_hdr.addWidget(self.tag_name_input)
        tag_layout.addLayout(tag_name_hdr)

        tag_thresh_hdr = QHBoxLayout()	# slouch threshold
        self.tag_thresh_label = QLabel("slouch angle threshold:", self)
        curr_thresh = float(self.config.get("tag_threshold_deg", 8.0))
        self.tag_thresh_val = QLabel(f"{curr_thresh:.1f}°", self)
        self.tag_thresh_val.setStyleSheet("color: #EF4444; font-weight: bold;")
        tag_thresh_hdr.addWidget(self.tag_thresh_label)
        tag_thresh_hdr.addStretch()
        tag_thresh_hdr.addWidget(self.tag_thresh_val)
        tag_layout.addLayout(tag_thresh_hdr)

        self.tag_thresh_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.tag_thresh_slider.setRange(30, 250)	# 3.0 to 25.0 deg
        self.tag_thresh_slider.setValue(int(curr_thresh * 10))
        self.tag_thresh_slider.valueChanged.connect(
            lambda v: self.tag_thresh_val.setText(f"{v / 10.0:.1f}°")
        )
        tag_layout.addWidget(self.tag_thresh_slider)

        tag_vib_hdr = QHBoxLayout()	# vibration alert
        self.tag_vib_lbl = QLabel("vibration alert:", self)
        self.tag_vib_combo = QComboBox(self)
        self.tag_vib_combo.setView(QListView())
        self.tag_vib_combo.addItem("only when tag is disconnected from laptop", 1)
        self.tag_vib_combo.addItem("both when connected and not", 2)
        self.tag_vib_combo.addItem("disabled", 0)
        tag_vib_hdr.addWidget(self.tag_vib_lbl)
        tag_vib_hdr.addWidget(self.tag_vib_combo, 1)
        tag_layout.addLayout(tag_vib_hdr)

        self.tag_status_hint = QLabel(self)	# tag connection status
        self.tag_status_hint.setWordWrap(True)
        tag_layout.addWidget(self.tag_status_hint)

        layout.addWidget(self.tag_group)

        self.cam_group = QGroupBox("camera input", self)	# camera selection
        cam_layout = QVBoxLayout(self.cam_group)
        cam_row = QHBoxLayout()
        cam_label = QLabel("active camera:", self)
        self.cam_combo = QComboBox(self)
        self.cam_combo.setView(QListView())
        self._populate_cameras()
        cam_row.addWidget(cam_label)
        cam_row.addWidget(self.cam_combo)
        cam_layout.addLayout(cam_row)
        layout.addWidget(self.cam_group)

        dim_group = QGroupBox("screen dimming && alerts", self)	# dimming settings
        dim_layout = QVBoxLayout(dim_group)

        op_header = QHBoxLayout()	# opacity slider
        op_label = QLabel("dimmer opacity:", self)
        curr_opacity = float(self.config.get('dim_opacity', 0.65))
        self.op_val_label = QLabel(f"{int(curr_opacity * 100)}%", self)
        self.op_val_label.setStyleSheet("color: #EF4444; font-weight: bold;")
        op_header.addWidget(op_label)
        op_header.addStretch()
        op_header.addWidget(self.op_val_label)
        dim_layout.addLayout(op_header)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.opacity_slider.setRange(20, 95)
        self.opacity_slider.setValue(int(curr_opacity * 100))
        self.opacity_slider.valueChanged.connect(lambda v: self.op_val_label.setText(f"{v}%"))
        dim_layout.addWidget(self.opacity_slider)

        grace_header = QHBoxLayout()	# grace period slider
        grace_label = QLabel("grace period:", self)
        curr_grace = float(self.config.get('grace_period_sec', 3.0))
        self.grace_val_label = QLabel(f"{curr_grace:.1f}s", self)
        self.grace_val_label.setStyleSheet("color: #EF4444; font-weight: bold;")
        grace_header.addWidget(grace_label)
        grace_header.addStretch()
        grace_header.addWidget(self.grace_val_label)
        dim_layout.addLayout(grace_header)

        self.grace_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.grace_slider.setRange(1, 10)
        self.grace_slider.setValue(int(curr_grace))
        self.grace_slider.valueChanged.connect(lambda v: self.grace_val_label.setText(f"{v}.0s"))
        dim_layout.addWidget(self.grace_slider)

        self.audio_check = QCheckBox("play sound alert when slouching", self)	# audio alerts
        self.audio_check.setChecked(bool(self.config.get("audio_alert", True)))
        self.audio_check.toggled.connect(self._on_audio_toggled)
        dim_layout.addWidget(self.audio_check)

        sound_row = QHBoxLayout()
        sound_label = QLabel("alert sound:", self)
        self.sound_combo = QComboBox(self)
        self.sound_combo.setView(QListView())
        self.sound_test_btn = QPushButton("test", self)
        self.sound_test_btn.setStyleSheet("""
            QPushButton {
                background-color: #27272A;
                color: #F4F4F5;
                padding: 6px 12px;
                border: 1px solid #3F3F46;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #2D1517;
                border-color: #DC2626;
                color: #FFFFFF;
            }
            QPushButton:disabled {
                background-color: #18181B;
                color: #52525B;
                border-color: #27272A;
            }
        """)
        self.sound_test_btn.clicked.connect(self._test_selected_sound)
        sound_row.addWidget(sound_label)
        sound_row.addWidget(self.sound_combo, 1)
        sound_row.addWidget(self.sound_test_btn)
        dim_layout.addLayout(sound_row)

        layout.addWidget(dim_group)

        btn_layout = QHBoxLayout()	# action buttons
        self.btn_restore = QPushButton("restore defaults", self)
        self.btn_restore.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #A1A1AA;
                border: 1px solid #3F3F46;
                font-size: 12px;
                font-weight: 500;
                padding: 6px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #27272A;
                color: #F4F4F5;
                border-color: #52525B;
            }
        """)
        self.btn_restore.clicked.connect(self.restore_defaults)

        self.btn_apply = QPushButton("apply", self)
        self.btn_apply.clicked.connect(self.apply_settings)
        btn_close = QPushButton("close", self)
        btn_close.setStyleSheet("background-color: #27272A; color: white;")
        btn_close.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_restore)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        btn_layout.addWidget(self.btn_apply)
        layout.addLayout(btn_layout)

        self._populate_sounds()
        self._refresh_visibility()

    def set_tag_connected(self, connected: bool):
        self._is_tag_connected = bool(connected)
        if connected:
            self._tag_status_override = None
            self._tag_status_is_error = False
        else:
            self._tag_battery_pct = -1
        self._refresh_visibility()

    def set_tag_battery(self, battery_pct: int):
        self._tag_battery_pct = battery_pct
        self._refresh_visibility()

    def set_tag_status_text(self, status: str, is_error: bool = False):
        self._tag_status_override = status.lower() if status else None
        self._tag_status_is_error = is_error
        self._refresh_visibility()

    def set_source(self, source: str):
        self.radio_tag.blockSignals(True)
        self.radio_camera.blockSignals(True)
        if source == "tag":
            self.radio_tag.setChecked(True)
            self.radio_camera.setChecked(False)
        else:
            self.radio_camera.setChecked(True)
            self.radio_tag.setChecked(False)
        self.radio_tag.blockSignals(False)
        self.radio_camera.blockSignals(False)
        self._refresh_visibility()

    def _on_source_toggled(self):
        self._refresh_visibility()
        new_source = "tag" if self.radio_tag.isChecked() else "camera"
        if self.config.get("perception_source") != new_source:
            self.config.set("perception_source", new_source)
            self.settings_changed.emit({"perception_source": new_source})

    def _refresh_visibility(self):
        is_tag = self.radio_tag.isChecked()
        self.tag_group.setEnabled(is_tag)
        self.cam_group.setEnabled(not is_tag)

        if is_tag:
            self.btn_cal_tag.setEnabled(self._is_tag_connected)
            self.btn_cal_cam.setEnabled(False)

            self.tag_name_lbl.setEnabled(True)	# tag name always editable so we can change it for finding the tag
            self.tag_name_input.setEnabled(True)

            connected = self._is_tag_connected	# threshold and vibration settings only work when tag is connected
            self.tag_thresh_label.setEnabled(connected)
            self.tag_thresh_slider.setEnabled(connected)
            self.tag_vib_lbl.setEnabled(connected)
            self.tag_vib_combo.setEnabled(connected)

            if connected:
                self.tag_thresh_val.setEnabled(True)
                self.tag_thresh_val.setStyleSheet("color: #EF4444; font-weight: bold;")
                bat_text = f" ({self._tag_battery_pct}%)" if getattr(self, '_tag_battery_pct', -1) >= 0 else ""
                self.tag_status_hint.setText(f"tag connected{bat_text}")
                self.tag_status_hint.setStyleSheet("color: #10B981; font-size: 11px;")
            else:
                self.tag_thresh_val.setEnabled(False)
                self.tag_thresh_val.setStyleSheet("color: #52525B; font-weight: bold;")
                status_text = self._tag_status_override or "tag disconnected"
                self.tag_status_hint.setText(status_text)
                if self._tag_status_is_error or "off" in status_text or "error" in status_text or "unavailable" in status_text:
                    self.tag_status_hint.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 500;")
                elif "connecting" in status_text or "scanning" in status_text:
                    self.tag_status_hint.setStyleSheet("color: #F59E0B; font-size: 11px;")
                else:
                    self.tag_status_hint.setStyleSheet("color: #71717A; font-size: 11px; font-style: italic;")
        else:
            self.btn_cal_tag.setEnabled(False)
            self.btn_cal_cam.setEnabled(True)
            self.tag_thresh_val.setStyleSheet("color: #52525B; font-weight: bold;")
            self.tag_status_hint.setText("")

    def _populate_cameras(self):
        self.cam_combo.clear()
        found_cams = []
        if os.name == "posix":
            import glob
            dev_nodes = sorted(glob.glob("/dev/video*"))
            for dev in dev_nodes:
                try:
                    idx = int(dev.replace("/dev/video", ""))
                    if idx not in found_cams and idx < 8:
                        found_cams.append(idx)
                except ValueError:
                    pass

        if not found_cams:
            for i in range(2):
                try:
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        found_cams.append(i)
                        cap.release()
                except Exception:
                    pass

        if not found_cams:
            found_cams = [0]

        for i in sorted(found_cams):
            self.cam_combo.addItem(f"camera device {i}", i)

        curr_cam = self.config.get("camera_index", 0)
        idx = self.cam_combo.findData(curr_cam)
        if idx >= 0:
            self.cam_combo.setCurrentIndex(idx)
        else:
            self.cam_combo.setCurrentIndex(0)

    def _populate_sounds(self):
        self.sound_combo.clear()
        sounds_dir = get_resource_path("assets/sounds")

        friendly_names = {
            "chime.wav": "chime",
            "notification-1.wav": "notification 1 (default)",
            "notification-2.wav": "notification 2",
            "notification-3.wav": "notification 3",
            "arcade-game-over.wav": "arcade game over",
            "windows-xp-error.wav": "windows xp error",
            "windows-xp-exclamation.wav": "windows xp exclamation",
        }

        found_sounds = []
        if sounds_dir.exists():
            for f in sorted(os.listdir(sounds_dir)):
                if f.lower().endswith(".wav"):
                    found_sounds.append(f)

        if not found_sounds:
            self.sound_combo.addItem("gentle chime", "chime.wav")
            return

        if "notification-1.wav" in found_sounds:	# put default notification-1.wav first
            found_sounds.remove("notification-1.wav")
            found_sounds.insert(0, "notification-1.wav")

        for sound_file in found_sounds:
            display_name = friendly_names.get(sound_file)
            if not display_name:
                base = os.path.splitext(sound_file)[0].replace("-", " ").replace("_", " ")
                display_name = base.lower()
            self.sound_combo.addItem(display_name, sound_file)

        curr_sound = self.config.get("audio_sound", "notification-1.wav")
        idx = self.sound_combo.findData(curr_sound)
        if idx >= 0:
            self.sound_combo.setCurrentIndex(idx)
        else:
            self.sound_combo.setCurrentIndex(0)

    def _test_selected_sound(self):
        sound_file = self.sound_combo.currentData()
        if not sound_file:
            return
        sounds_dir = get_resource_path("assets/sounds")
        path = sounds_dir / sound_file
        if path.exists():
            play_audio_file(path)

    def _on_audio_toggled(self, checked: bool):
        self.sound_combo.setEnabled(checked)
        self.sound_test_btn.setEnabled(checked)

    def showEvent(self, event):
        super().showEvent(event)
        current_source = self.config.get("perception_source", "tag")
        if current_source == "tag":
            self.radio_tag.setChecked(True)
        else:
            self.radio_camera.setChecked(True)

        curr_thresh = float(self.config.get("tag_threshold_deg", 8.0))
        self.tag_thresh_slider.setValue(int(curr_thresh * 10))
        self.tag_thresh_val.setText(f"{curr_thresh:.1f}°")
        self.tag_name_input.setText(self.config.get("tag_name", "slouchd-tag"))

        curr_vib = int(self.config.get("tag_vibration_mode", 1))
        vib_idx = self.tag_vib_combo.findData(curr_vib)
        if vib_idx >= 0:
            self.tag_vib_combo.setCurrentIndex(vib_idx)

        curr_opacity = float(self.config.get('dim_opacity', 0.65))
        self.opacity_slider.setValue(int(curr_opacity * 100))
        self.op_val_label.setText(f"{int(curr_opacity * 100)}%")

        curr_grace = float(self.config.get('grace_period_sec', 1.0))
        self.grace_slider.setValue(int(curr_grace))
        self.grace_val_label.setText(f"{curr_grace:.1f}s")

        is_audio = bool(self.config.get("audio_alert", True))
        self.audio_check.setChecked(is_audio)
        self._populate_sounds()
        self._on_audio_toggled(is_audio)

        self._refresh_visibility()

    def _calibrate_tag(self):
        self.radio_tag.setChecked(True)
        self.apply_settings()
        self.accept()
        self.calibrate_requested.emit()

    def _calibrate_cam(self):
        self.radio_camera.setChecked(True)
        self.apply_settings()
        self.accept()
        self.calibrate_requested.emit()

    def apply_settings(self):
        source = "tag" if self.radio_tag.isChecked() else "camera"
        new_settings = {
            "perception_source": source,
            "tag_name": self.tag_name_input.text().strip() or "slouchd-tag",
            "tag_threshold_deg": self.tag_thresh_slider.value() / 10.0,
            "tag_vibration_mode": self.tag_vib_combo.currentData() if self.tag_vib_combo.currentData() is not None else 1,
            "camera_index": self.cam_combo.currentData() if self.cam_combo.currentData() is not None else 0,
            "dim_opacity": self.opacity_slider.value() / 100.0,
            "grace_period_sec": float(self.grace_slider.value()),
            "audio_alert": self.audio_check.isChecked(),
            "audio_sound": self.sound_combo.currentData() or "notification-1.wav",
        }
        self.config.update(new_settings)
        self.settings_changed.emit(new_settings)
        self.btn_apply.setText("applied")
        QTimer.singleShot(1000, lambda: self.btn_apply.setText("apply"))
        return new_settings

    def save_settings(self):
        self.apply_settings()
        self.accept()

    def restore_defaults(self):
        default_source = DEFAULT_CONFIG.get("perception_source", "camera")
        if default_source == "tag":
            self.radio_tag.setChecked(True)
        else:
            self.radio_camera.setChecked(True)

        def_name = DEFAULT_CONFIG.get("tag_name", "slouchd-tag")
        self.tag_name_input.setText(def_name)

        def_thresh = float(DEFAULT_CONFIG.get("tag_threshold_deg", 8.0))
        self.tag_thresh_slider.setValue(int(def_thresh * 10))
        self.tag_thresh_val.setText(f"{def_thresh:.1f}°")

        def_vib = int(DEFAULT_CONFIG.get("tag_vibration_mode", 1))
        vib_idx = self.tag_vib_combo.findData(def_vib)
        if vib_idx >= 0:
            self.tag_vib_combo.setCurrentIndex(vib_idx)

        if self.cam_combo.count() > 0:
            self.cam_combo.setCurrentIndex(0)

        def_opacity = float(DEFAULT_CONFIG.get("dim_opacity", 0.65))
        self.opacity_slider.setValue(int(def_opacity * 100))
        self.op_val_label.setText(f"{int(def_opacity * 100)}%")

        def_grace = float(DEFAULT_CONFIG.get("grace_period_sec", 1.0))
        self.grace_slider.setValue(int(def_grace))
        self.grace_val_label.setText(f"{def_grace:.1f}s")

        def_audio = bool(DEFAULT_CONFIG.get("audio_alert", True))
        self.audio_check.setChecked(def_audio)
        self._on_audio_toggled(def_audio)

        def_sound = DEFAULT_CONFIG.get("audio_sound", "notification-1.wav")
        sound_idx = self.sound_combo.findData(def_sound)
        if sound_idx >= 0:
            self.sound_combo.setCurrentIndex(sound_idx)

        self._refresh_visibility()

        self.btn_restore.setText("restored")
        QTimer.singleShot(1000, lambda: self.btn_restore.setText("restore defaults"))
