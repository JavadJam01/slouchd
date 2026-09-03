from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QMessageBox, QWidget, QFrame
)
from PySide6.QtGui import QPixmap, QFont, QPainter, QColor, QPen, QBrush

class TagPostureMeter(QWidget):
    """tilt gauge widget for tag"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(592, 280)
        self.pitch = 0.0
        self.roll = 0.0
        self.baseline_pitch = 0.0
        self.delta = 0.0
        self.threshold = 8.0
        self.is_slouching = False
        self.is_connected = False
        self.is_calibrated = False
        self.battery = -1
        self.status_message = "waiting for tag connection..."

    def set_status_message(self, msg: str):
        self.status_message = msg.lower() if msg else "waiting for tag connection..."
        self.update()

    def update_metrics(self, data: dict):
        self.pitch = data.get("pitch", 0.0)
        self.roll = data.get("roll", 0.0)
        self.baseline_pitch = data.get("baseline_pitch", 0.0)
        self.delta = data.get("delta", 0.0)
        self.is_slouching = data.get("is_slouching", False)
        self.is_calibrated = data.get("calibrated", False)
        if "battery" in data and data["battery"] >= 0:
            self.battery = data["battery"]
        self.is_connected = True
        self.update()

    def set_disconnected(self):
        self.is_connected = False
        self.battery = -1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setBrush(QColor("#18181B"))	# background
        painter.setPen(QPen(QColor("#27272A"), 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)

        if not self.is_connected:
            if "off" in self.status_message or "error" in self.status_message or "unavailable" in self.status_message:
                painter.setPen(QColor("#EF4444"))
            elif "connecting" in self.status_message or "scanning" in self.status_message:
                painter.setPen(QColor("#F59E0B"))
            else:
                painter.setPen(QColor("#71717A"))
            painter.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.status_message)
            painter.end()
            return

        cx = self.width() // 2
        cy = 130

        painter.setPen(QColor("#A1A1AA"))	# title
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        painter.drawText(20, 30, "collar tag orientation")

        badge_text = "slouching" if self.is_slouching else ("upright" if self.is_calibrated else "uncalibrated")	# status badge
        badge_color = QColor("#EF4444") if self.is_slouching else (QColor("#10B981") if self.is_calibrated else QColor("#F59E0B"))
        
        painter.setBrush(badge_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.width() - 140, 16, 120, 24, 12, 12)
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(self.width() - 140, 16, 120, 24, Qt.AlignmentFlag.AlignCenter, badge_text)

        if self.battery >= 0:	# battery badge
            bat_color = QColor("#10B981") if self.battery > 20 else (QColor("#F59E0B") if self.battery > 10 else QColor("#EF4444"))
            painter.setBrush(QColor("#27272A"))
            painter.setPen(QPen(bat_color, 1))
            painter.drawRoundedRect(self.width() - 230, 16, 80, 24, 12, 12)
            painter.setPen(QColor("#E4E4E7"))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            painter.drawText(self.width() - 230, 16, 80, 24, Qt.AlignmentFlag.AlignCenter, f"{self.battery}% bat")

        meter_w = 400	# pitch meter bar
        meter_h = 16
        meter_x = (self.width() - meter_w) // 2
        meter_y = 110

        painter.setBrush(QColor("#27272A"))	# meter track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(meter_x, meter_y, meter_w, meter_h, 8, 8)

        center_x = meter_x + meter_w // 2	# baseline marker
        painter.setPen(QPen(QColor("#10B981"), 2, Qt.PenStyle.DashLine))
        painter.drawLine(center_x, meter_y - 8, center_x, meter_y + meter_h + 8)

        clamped_delta = max(-30.0, min(30.0, self.delta))	# map delta to meter width (-30 to +30)
        delta_offset_px = int((clamped_delta / 30.0) * (meter_w / 2))
        indicator_x = center_x + delta_offset_px

        ind_color = QColor("#EF4444") if self.is_slouching else QColor("#10B981")	# indicator dot
        painter.setBrush(ind_color)
        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.drawEllipse(indicator_x - 8, meter_y - 2, 20, 20)

        thresh_px = int((self.threshold / 30.0) * (meter_w / 2))	# threshold line
        painter.setPen(QPen(QColor("#EF4444"), 2, Qt.PenStyle.DotLine))
        painter.drawLine(center_x + thresh_px, meter_y - 6, center_x + thresh_px, meter_y + meter_h + 6)

        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))	# readings
        painter.setPen(QColor("#E4E4E7"))

        col1_x = 40
        col2_x = 180
        col3_x = 320
        col4_x = 460
        row_y = 190

        painter.setFont(QFont("Segoe UI", 10))
        painter.setPen(QColor("#71717A"))
        painter.drawText(col1_x, row_y, "pitch")
        painter.drawText(col2_x, row_y, "roll")
        painter.drawText(col3_x, row_y, "pitch delta")
        painter.drawText(col4_x, row_y, "slouch threshold")

        painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        painter.setPen(QColor("#F4F4F5"))
        painter.drawText(col1_x, row_y + 30, f"{self.pitch:+.1f}°")
        painter.drawText(col2_x, row_y + 30, f"{self.roll:+.1f}°")

        delta_color = QColor("#EF4444") if self.delta > self.threshold else QColor("#10B981")
        painter.setPen(delta_color)
        painter.drawText(col3_x, row_y + 30, f"{self.delta:+.1f}°")

        painter.setPen(QColor("#EF4444"))
        painter.drawText(col4_x, row_y + 30, f"{self.threshold:.1f}°")

        painter.setFont(QFont("Segoe UI", 10))	# instruction text
        painter.setPen(QColor("#A1A1AA"))
        painter.drawText(self.rect().adjusted(20, 240, -20, 0), Qt.AlignmentFlag.AlignLeft,
                         "green: baseline upright, red: slouch threshold")

        painter.end()


class CalibrationDialog(QDialog):
    calibrated = Signal(dict)
    tag_calibrate_requested = Signal()

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.latest_metrics = None
        self.perception_source = self.config.get("perception_source", "tag")
        
        self._is_calibrating = False
        self._samples = []
        self._target_samples = 20

        self.setWindowTitle("slouchd — posture calibration")
        self.setFixedSize(640, 560)
        self.setStyleSheet("""
            QDialog {
                background-color: #121215;
                background-color: #000000;
                color: #E4E4E7;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QLabel {
                color: #A1A1AA;
            }
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                font-weight: 600;
                font-size: 13px;
                padding: 9px 18px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #EF4444;
            }
            QPushButton:disabled {
                background-color: #27272A;
                color: #71717A;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        self.title = QLabel("posture calibration", self)
        self.title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.title.setStyleSheet("color: #FAFAFA;")
        layout.addWidget(self.title)

        self.desc = QLabel(self)
        self.desc.setWordWrap(True)
        self.desc.setStyleSheet("color: #A1A1AA; font-size: 13px; line-height: 1.4;")
        layout.addWidget(self.desc)

        self.tag_meter = TagPostureMeter(self)	# tag meter widget
        layout.addWidget(self.tag_meter)

        self.preview_label = QLabel(self)	# camera preview
        self.preview_label.setFixedSize(592, 280)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("""
            background-color: #18181B;
            border: 1px solid #27272A;
            border-radius: 8px;
        """)
        self.preview_label.setText("connecting to video stream...")
        layout.addWidget(self.preview_label)

        meter_layout = QHBoxLayout()	# progress bar
        self.meter_label = QLabel("tracking status:", self)
        self.meter_label.setStyleSheet("font-size: 12px; font-weight: 500;")
        
        self.visibility_bar = QProgressBar(self)
        self.visibility_bar.setRange(0, 100)
        self.visibility_bar.setValue(0)
        self.visibility_bar.setFixedHeight(8)
        self.visibility_bar.setTextVisible(False)
        self.visibility_bar.setStyleSheet("""
            QProgressBar {
                background-color: #27272A;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #10B981;
                border-radius: 4px;
            }
        """)
        meter_layout.addWidget(self.meter_label)
        meter_layout.addWidget(self.visibility_bar)
        layout.addLayout(meter_layout)

        btn_layout = QHBoxLayout()	# action buttons
        self.btn_calibrate = QPushButton("calibrate baseline", self)
        self.btn_calibrate.clicked.connect(self.start_calibration)
        
        self.btn_close = QPushButton("cancel", self)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: #27272A;
                color: #E4E4E7;
            }
            QPushButton:hover {
                background-color: #3F3F46;
            }
        """)
        self.btn_close.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_close)
        btn_layout.addWidget(self.btn_calibrate)
        layout.addLayout(btn_layout)

        self._apply_mode()

    def set_tag_status_text(self, text: str, is_error: bool = False):
        if not self.tag_meter.is_connected:
            self.tag_meter.set_status_message(text)

    def set_tag_battery(self, battery_pct: int):
        if hasattr(self, 'tag_meter'):
            self.tag_meter.battery = battery_pct
            self.tag_meter.update()

    def set_camera_error(self, err_msg: str):
        if self.perception_source == "camera":
            self.preview_label.clear()
            self.preview_label.setText("camera unavailable\ncheck if another app is using webcam")
            self.preview_label.setStyleSheet("""
                background-color: #18181B;
                border: 1px solid #7F1D1D;
                border-radius: 8px;
                color: #EF4444;
                font-size: 13px;
                font-weight: 500;
            """)
            self.visibility_bar.setValue(0)
            self.meter_label.setText("camera error")

    def set_source(self, source: str):
        self.perception_source = source
        self._is_calibrating = False
        self._samples.clear()
        self.btn_calibrate.setText("calibrate baseline")
        self.btn_calibrate.setEnabled(True)
        self.visibility_bar.setValue(0)
        self.latest_metrics = None
        if source == "camera":
            self.preview_label.setText("connecting to video stream...")
            self.preview_label.setStyleSheet("""
                background-color: #18181B;
                border: 1px solid #27272A;
                border-radius: 8px;
                color: #A1A1AA;
                font-size: 13px;
            """)
        self._apply_mode()

    def _apply_mode(self):
        if self.perception_source == "tag":
            self.tag_meter.threshold = float(self.config.get("tag_threshold_deg", 8.0))
            self.tag_meter.show()
            self.preview_label.hide()
            self.desc.setText(
                "clip the tag to your shirt collar.\n"
                "sit up straight, then click calibrate baseline."
            )
            self.meter_label.setText("tag calibration:")
        else:
            self.tag_meter.hide()
            self.preview_label.show()
            self.desc.setText(
                "sit upright facing the camera.\n"
                "ensure head and shoulders are visible, then click calibrate baseline."
            )
            self.meter_label.setText("tracking quality:")

    def showEvent(self, event):
        super().showEvent(event)
        self.perception_source = self.config.get("perception_source", "tag")
        self._is_calibrating = False
        self._samples.clear()
        self.btn_calibrate.setText("calibrate baseline")
        self.btn_calibrate.setEnabled(True)
        self.visibility_bar.setValue(0)
        self.latest_metrics = None
        if self.perception_source == "camera":
            self.preview_label.setText("connecting to video stream...")
            self.preview_label.setStyleSheet("""
                background-color: #18181B;
                border: 1px solid #27272A;
                border-radius: 8px;
                color: #A1A1AA;
                font-size: 13px;
            """)
        self._apply_mode()

    def update_tag_data(self, data: dict):
        if self.perception_source == "tag":
            self.tag_meter.update_metrics(data)
            if self._is_calibrating:
                self._samples.append(data.get("pitch", 0.0))
                progress = int((len(self._samples) / float(self._target_samples)) * 100)
                self.visibility_bar.setValue(progress)
                self.meter_label.setText(f"calibrating: {progress}% (hold still...)")

                if len(self._samples) >= self._target_samples:
                    self._finalize_tag_calibration()

    def update_frame(self, qimg, metrics):
        if self.perception_source != "camera":
            return

        self.latest_metrics = metrics
        if qimg is not None and not qimg.isNull():
            self.preview_label.setStyleSheet("""
                background-color: #18181B;
                border: 1px solid #27272A;
                border-radius: 8px;
            """)
            scaled_pixmap = QPixmap.fromImage(qimg).scaled(
                self.preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled_pixmap)
            if not self._is_calibrating:
                self.meter_label.setText("tracking quality:")

        visibility = int(metrics.get("visibility", 0.0) * 100)
        
        if not self._is_calibrating:
            self.visibility_bar.setValue(visibility)
        else:
            if metrics and metrics.get("visibility", 0.0) >= 0.35 and "normalized_ear_shoulder" in metrics:
                self._samples.append(metrics)
                progress = int((len(self._samples) / float(self._target_samples)) * 100)
                self.visibility_bar.setValue(progress)
                self.meter_label.setText(f"calibrating: {progress}% (hold still...)")

                if len(self._samples) >= self._target_samples:
                    self._finalize_camera_calibration()

    def start_calibration(self):
        if self.perception_source == "tag":
            if not self.tag_meter.is_connected:
                QMessageBox.warning(
                    self,
                    "tag not connected",
                    "ensure slouchd-tag is turned on and connected."
                )
                return
            self._is_calibrating = True
            self._samples.clear()
            self.btn_calibrate.setEnabled(False)
            self.btn_calibrate.setText("sampling posture...")
            self.visibility_bar.setValue(0)
            self.meter_label.setText("calibrating: 0% (hold still...)")
        else:
            if not self.latest_metrics or self.latest_metrics.get("visibility", 0) < 0.35:
                QMessageBox.warning(
                    self,
                    "calibration warning",
                    "position head and shoulders in view before calibrating."
                )
                return

            self._is_calibrating = True
            self._samples.clear()
            self.btn_calibrate.setEnabled(False)
            self.btn_calibrate.setText("sampling posture...")
            self.visibility_bar.setValue(0)
            self.meter_label.setText("calibrating: 0% (hold still...)")

    def _finalize_tag_calibration(self):
        self._is_calibrating = False
        avg_pitch = sum(self._samples) / float(len(self._samples))
        self.config.set("tag_baseline_pitch", float(avg_pitch))
        self.config.set("tag_calibrated", True)

        self.tag_calibrate_requested.emit()
        self.calibrated.emit({"source": "tag", "baseline_pitch": avg_pitch, "calibrated": True})

        QMessageBox.information(
            self,
            "calibration complete",
            f"tag calibrated at {avg_pitch:.1f}° baseline."
        )
        self.accept()

    def _finalize_camera_calibration(self):
        self._is_calibrating = False
        n = float(len(self._samples))
        
        avg_ear_shoulder = sum(s["ear_shoulder_dist"] for s in self._samples) / n
        avg_norm_ear_shoulder = sum(s["normalized_ear_shoulder"] for s in self._samples) / n
        avg_shoulder_width = sum(s["shoulder_width"] for s in self._samples) / n
        avg_inter_ear = sum(s["inter_ear_dist"] for s in self._samples) / n
        avg_nose_shoulder = sum(s.get("nose_shoulder_dist", avg_ear_shoulder * 1.2) for s in self._samples) / n

        baseline_data = {
            "calibrated": True,
            "ear_shoulder_dist": float(avg_ear_shoulder),
            "nose_shoulder_dist": float(avg_nose_shoulder),
            "normalized_ear_shoulder": float(avg_norm_ear_shoulder),
            "shoulder_width": float(avg_shoulder_width),
            "inter_ear_dist": float(avg_inter_ear)
        }

        self.config.set("baseline", baseline_data)
        self.calibrated.emit(baseline_data)
        QMessageBox.information(
            self,
            "calibration complete",
            "baseline posture calibrated successfully."
        )
        self.accept()
