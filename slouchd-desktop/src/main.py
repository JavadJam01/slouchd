import sys
import os
import time
import signal
import threading
import tempfile
import wave
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))	# add project root to path

from src import __version__
from src.config import ConfigManager, get_resource_path
from src.logging_config import setup_logging
from src.startup import set_startup_enabled
from src.audio import play_audio_file
from src.hotkey import GlobalHotkey
from src.camera.worker import CameraWorker
from src.ble.worker import BleTagWorker
from src.ui.overlay import MultiScreenDimmer
from src.ui.system_tray import SlouchdTrayIcon
from src.ui.main_window import SlouchdWindow
from src.ui.calibration_hud import CalibrationHUD, PositionPromptHUD
from src.ui.updater import PeriodicUpdateChecker

class SlouchdApp:
    def __init__(self):
        signal.signal(signal.SIGINT, signal.SIG_DFL)	# enable sigint (ctrl+c) handling

        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("slouchd.desktop.app")
            except Exception:
                pass

        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setApplicationName("slouchd")

        icon_path = get_resource_path("assets/icon.png")
        if icon_path.exists():
            self.app_icon = QIcon(str(icon_path))
            self.app.setWindowIcon(self.app_icon)

        self.sigint_timer = QTimer()	# let python handle sigint
        self.sigint_timer.start(500)
        self.sigint_timer.timeout.connect(lambda: None)

        self.config = ConfigManager()
        self.dimmer = MultiScreenDimmer(self.config)
        self.tray = SlouchdTrayIcon()

        self._calibrating = False
        self._calib_samples = []
        self._calib_cooldown_until = 0.0
        self._calib_hud = CalibrationHUD()
        self._prompt_hud = PositionPromptHUD()
        self._prompt_hud.recalibrate_requested.connect(self.trigger_shortcut_calibration)
        self._prompt_hud.pause_requested.connect(self._on_prompt_pause_requested)
        self.dimmer.register_hud(self._prompt_hud)
        self.dimmer.register_hud(self._calib_hud)

        self._alarm_history = []
        self._sustained_timer = QTimer()
        self._sustained_timer.setSingleShot(True)
        self._sustained_timer.timeout.connect(self._on_sustained_slouch)

        self.hotkey = GlobalHotkey()
        self.hotkey.activated.connect(self.trigger_shortcut_calibration)

        self._was_slouching = False
        self._tag_slouch_start = 0.0
        self._tag_connected = False
        self._latest_tag_data = None
        self._camera_error_notified = False
        self._init_audio()	# init audio

        # presence and welcome back tracking
        self._last_user_active_time = time.time()
        self._last_presence_tick = time.time()
        self._user_was_away = False
        self._last_welcome_shown_time = 0.0
        self._startup_welcome_pending = True
        self._camera_away_start = 0.0
        self._tag_disconnect_time = 0.0

        self._presence_timer = QTimer(self.app)
        self._presence_timer.timeout.connect(self._check_user_presence)
        self._presence_timer.start(1000)

        self.ble_worker = BleTagWorker(self.config)	# workers setup
        self.camera_worker = CameraWorker(self.config)

        self.main_window = SlouchdWindow(self.config)
        self.main_window.tag_calibrate_requested.connect(self.ble_worker.calibrate)
        self.main_window.settings_changed.connect(self.on_settings_changed)
        self.main_window.camera_preview_needed.connect(self.on_camera_preview_needed)

        self.ble_worker.tag_connected.connect(self.on_tag_connected)	# connect ble signals
        self.ble_worker.tag_data.connect(self.on_tag_data)
        self.ble_worker.tag_battery.connect(self.on_tag_battery)
        self.ble_worker.tag_status.connect(self.on_tag_status)
        self.ble_worker.tag_error.connect(self.on_tag_error)

        self.camera_worker.frame_ready.connect(self.on_camera_frame_ready)	# connect camera signals
        self.camera_worker.camera_error.connect(self.on_camera_error)

        self.tray.calibrate_requested.connect(self.open_calibration)	# connect tray signals
        self.tray.settings_requested.connect(self.open_settings)
        self.tray.toggle_pause_requested.connect(self.on_pause_toggled)
        self.tray.source_changed.connect(self.switch_perception_source)
        self.tray.exit_requested.connect(self.exit_app)

        self.tray.show()

        self.camera_worker.start()	# start workers
        self.ble_worker.start()

        curr_source = self.config.get("perception_source", "tag")	# start active perception source
        self.tray.set_source(curr_source)
        self.apply_perception_source(curr_source)

        self._check_initial_calibration()	# check initial calibration

        # background periodic update checker
        self._last_update_res = None
        self.update_checker = PeriodicUpdateChecker(__version__, parent=self.app)
        self.update_checker.update_available.connect(self._on_update_available)
        self.tray.messageClicked.connect(self._on_tray_message_clicked)
        self.update_checker.start(initial_delay_sec=15)

    def _on_update_available(self, res: dict):
        self._last_update_res = res
        latest = res.get("latest_version")
        self.main_window.options_btn.set_update_available(True, latest_res=res)
        self.tray.showMessage(
            "slouchd update available",
            f"version v{latest} is available. click to download and update.",
            SlouchdTrayIcon.MessageIcon.Information,
            8000
        )

    def _on_tray_message_clicked(self):
        if self._last_update_res:
            self.main_window.open_update_dialog(self._last_update_res)
            self._last_update_res = None

    def _check_initial_calibration(self):
        source = self.config.get("perception_source", "tag")
        if source == "tag":
            is_calibrated = bool(self.config.get("tag_calibrated", False))
            self.tray.update_status(is_calibrated=is_calibrated, is_slouching=False, user_present=bool(self._tag_connected))
        else:
            baseline = self.config.get("baseline", {})
            is_calibrated = bool(baseline.get("calibrated", False))
            self.tray.update_status(is_calibrated=is_calibrated, is_slouching=False, user_present=False)

        if not is_calibrated:
            self.tray.showMessage(
                "slouchd",
                "calibrate your upright posture to begin monitoring",
                SlouchdTrayIcon.MessageIcon.Information,
                5000
            )
            QTimer.singleShot(800, self.open_calibration)

    def apply_perception_source(self, source: str):
        self.dimmer.set_dimmed(False)
        if self._was_slouching:
            self._handle_slouch_ended()
        self._was_slouching = False
        self._tag_slouch_start = 0.0
        self._camera_away_start = 0.0

        if not self.camera_worker.isRunning():
            self.camera_worker.start()
        if not self.ble_worker.isRunning():
            self.ble_worker.start()

        is_calibrating = bool(self.main_window.isVisible() and self.main_window.tabs.currentIndex() == 0)

        if source == "tag":
            self.camera_worker.set_preview_mode(False)	# tag mode: release camera and unpause ble
            self.camera_worker.set_paused(True)
            self.ble_worker.set_paused(self.tray.is_paused)
        else:
            self.ble_worker.set_paused(True)	# camera mode: pause ble and start camera
            self.camera_worker.set_paused(self.tray.is_paused)
            if is_calibrating:
                self.camera_worker.set_paused(False)
                self.camera_worker.set_preview_mode(True)
            else:
                self.camera_worker.set_preview_mode(False)
                self.camera_worker.set_paused(self.tray.is_paused)

        self.tray.set_source(source)
        self.main_window.set_source(source)

    @Slot(str)
    def switch_perception_source(self, source: str):
        self.config.set("perception_source", source)
        self.apply_perception_source(source)

    @Slot(bool, str)	# ble handlers
    def on_tag_connected(self, is_connected: bool, dev_name: str):
        prev_connected = self._tag_connected
        self._tag_connected = is_connected
        self.tray.set_tag_status(is_connected)
        self.main_window.set_tag_connected(is_connected)
        if is_connected:
            clean_name = dev_name.lower() if dev_name else "slouchd-tag"
            self.tray.showMessage(
                "tag connected",
                f"connected to {clean_name}",
                SlouchdTrayIcon.MessageIcon.Information,
                3000
            )
            if self._tag_disconnect_time > 0.0:
                away_duration = time.time() - self._tag_disconnect_time
                self._tag_disconnect_time = 0.0
                away_threshold = float(self.config.get("welcome_back_away_sec", 120.0))
                if away_duration >= away_threshold:
                    self._show_welcome_back()
        else:
            if self._tag_disconnect_time == 0.0:
                self._tag_disconnect_time = time.time()
            if self._calibrating:
                self._calibrating = False
                self._calib_hud.show_error("tag disconnected")
            self.dimmer.set_dimmed(False)
            if self._was_slouching:
                self._handle_slouch_ended()
            self._was_slouching = False
            self._tag_slouch_start = 0.0
            self.tray.update_status(is_calibrated=False, is_slouching=False, user_present=False)
            if prev_connected:
                self.tray.showMessage(
                    "tag disconnected",
                    "attempting to reconnect...",
                    SlouchdTrayIcon.MessageIcon.Warning,
                    3000
                )

    @Slot(int)
    def on_tag_battery(self, bat_pct: int):
        self.tray.set_tag_status(True, bat_pct)
        self.main_window.set_tag_battery(bat_pct)

    @Slot(str)
    def on_tag_status(self, msg: str):
        clean_msg = msg.lower()
        self.tray.set_tag_status_text(clean_msg)
        self.main_window.set_tag_status_text(clean_msg)

    @Slot(str)
    def on_tag_error(self, err: str):
        err_lower = err.lower()
        clean_err = "bluetooth error"
        if "not installed" in err_lower or "missing" in err_lower:
            clean_err = "bluetooth library unavailable"
        elif "off" in err_lower or "adapter" in err_lower or "disabled" in err_lower or "power" in err_lower:
            clean_err = "bluetooth is off"
        elif "scan" in err_lower:
            clean_err = "bluetooth off or tag not found"
        elif "connection" in err_lower or "timeout" in err_lower:
            clean_err = "tag connection error"

        self.tray.set_tag_status_text(clean_err, is_error=True)
        self.main_window.set_tag_status_text(clean_err, is_error=True)

    @Slot(dict)
    def on_tag_data(self, data: dict):
        self._latest_tag_data = data

        if "battery" in data and data["battery"] >= 0:
            if self.tray.battery_pct < 0:
                self.tray.set_tag_status(True, data["battery"])
            if self.main_window.tag_battery_pct < 0:
                self.main_window.set_tag_battery(data["battery"])

        self.main_window.update_tag_data(data)

        if self._startup_welcome_pending and self.config.get("perception_source", "tag") == "tag":
            self._startup_welcome_pending = False
            self._show_welcome_back()

        if self._calibrating and self.config.get("perception_source", "tag") == "tag":
            pitch = data.get("pitch")
            if pitch is not None:
                self._calib_samples.append(float(pitch))
                pct = int((len(self._calib_samples) / 20.0) * 100)
                self._calib_hud.show_progress(pct, "calibrating...")
                if len(self._calib_samples) >= 20:
                    self._finalize_shortcut_calibration()
            return

        if self.config.get("perception_source", "tag") != "tag":
            return

        if self.tray.is_paused or self._calibrating or (time.time() < self._calib_cooldown_until):
            self.dimmer.set_dimmed(False)
            if self._was_slouching:
                self._handle_slouch_ended()
            self._was_slouching = False
            self._tag_slouch_start = 0.0
            return

        is_calibrated = bool(data.get("calibrated", False) or self.config.get("tag_calibrated", False))
        is_tag_slouch = bool(data.get("is_slouching", False))

        if not is_calibrated:
            self.dimmer.set_dimmed(False)
            if self._was_slouching:
                self._handle_slouch_ended()
            self._was_slouching = False
            self.tray.update_status(is_calibrated=False, is_slouching=False, user_present=True)
            return

        grace_period = float(self.config.get("grace_period_sec", 1.0))	# handle grace period
        now = time.time()

        if is_tag_slouch:
            if self._tag_slouch_start == 0.0:
                self._tag_slouch_start = now
            slouch_duration = now - self._tag_slouch_start
            confirmed_slouch = (slouch_duration >= grace_period)
        else:
            self._tag_slouch_start = 0.0
            confirmed_slouch = False

        if confirmed_slouch:
            if not self._was_slouching:
                if self.config.get("audio_alert", True):
                    self.play_chime()
                self._handle_slouch_started()
            self.dimmer.set_dimmed(True)
        else:
            if self._was_slouching:
                self._handle_slouch_ended()
            self.dimmer.set_dimmed(False)

        self._was_slouching = confirmed_slouch
        self.tray.update_status(is_calibrated=True, is_slouching=confirmed_slouch, user_present=True)

    @Slot(object, dict, bool, float)	# camera handlers
    def on_camera_frame_ready(self, qimg, metrics, is_slouching, slouch_ratio):
        if self.config.get("perception_source", "tag") != "camera":
            return

        self._camera_error_notified = False

        if qimg is not None:
            self.main_window.update_frame(qimg, metrics)

        if self._calibrating and self.config.get("perception_source", "tag") == "camera":
            if metrics and metrics.get("visibility", 0.0) >= 0.35 and "normalized_ear_shoulder" in metrics:
                self._calib_samples.append(metrics)
                pct = int((len(self._calib_samples) / 20.0) * 100)
                self._calib_hud.show_progress(pct, "calibrating...")
                if len(self._calib_samples) >= 20:
                    self._finalize_shortcut_calibration()
            return

        if self.tray.is_paused or self._calibrating or (time.time() < self._calib_cooldown_until):
            self.dimmer.set_dimmed(False)
            if self._was_slouching:
                self._handle_slouch_ended()
            self._was_slouching = False
            return

        baseline = self.config.get("baseline", {})
        is_calibrated = bool(baseline.get("calibrated", False))
        user_present = bool(metrics and metrics.get("visibility", 0.0) >= 0.25)
        now = time.time()

        if user_present:
            if self._startup_welcome_pending:
                self._startup_welcome_pending = False
                self._show_welcome_back()
            elif self._camera_away_start > 0.0:
                away_duration = now - self._camera_away_start
                self._camera_away_start = 0.0
                away_threshold = float(self.config.get("welcome_back_away_sec", 120.0))
                if away_duration >= away_threshold:
                    self._show_welcome_back()
            self._last_user_active_time = now
        else:
            if self._camera_away_start == 0.0:
                self._camera_away_start = now

        if not is_calibrated or not user_present:
            self.dimmer.set_dimmed(False)
            if self._was_slouching:
                self._handle_slouch_ended()
            self._was_slouching = False
            self.tray.update_status(is_calibrated=is_calibrated, is_slouching=False, user_present=user_present)
            return

        if is_slouching:
            if not self._was_slouching:
                if self.config.get("audio_alert", True):
                    self.play_chime()
                self._handle_slouch_started()
            self.dimmer.set_dimmed(True)
        else:
            if self._was_slouching:
                self._handle_slouch_ended()
            self.dimmer.set_dimmed(False)

        self._was_slouching = is_slouching
        self.tray.update_status(is_calibrated=True, is_slouching=is_slouching, user_present=True)

    def _init_audio(self):
        self._chime_wav_path = None
        try:
            sounds_dir = get_resource_path("assets/sounds")
            sound_name = self.config.get("audio_sound", "notification-1.wav")
            wav_path = sounds_dir / sound_name

            if not wav_path.exists():
                default_path = sounds_dir / "notification-1.wav"
                if default_path.exists():
                    wav_path = default_path
                else:
                    wavs = [sounds_dir / f for f in os.listdir(sounds_dir) if f.endswith(".wav")] if sounds_dir.exists() else []
                    if wavs:
                        wav_path = wavs[0]

            if wav_path.exists():
                self._chime_wav_path = str(wav_path)
        except Exception:
            pass

    def play_chime(self):
        try:
            if self._chime_wav_path:
                play_audio_file(self._chime_wav_path)
            else:
                QApplication.beep()
        except Exception:
            pass

    @Slot(str)
    def on_camera_error(self, err_msg):
        self.main_window.set_camera_error(err_msg)
        if self.config.get("perception_source", "tag") == "camera":
            if not self._camera_error_notified:
                self._camera_error_notified = True
                self.tray.showMessage(
                    "camera alert",
                    "camera unavailable or in use by another app",
                    SlouchdTrayIcon.MessageIcon.Warning,
                    4000
                )
            self.dimmer.set_dimmed(False)
            self.tray.update_status(is_calibrated=False, is_slouching=False, user_present=False)

    def _handle_slouch_started(self):
        now = time.time()
        window_sec = float(self.config.get("position_prompt_window_sec", 35.0))
        alarm_count = int(self.config.get("position_prompt_alarm_count", 3))
        sustained_sec = float(self.config.get("position_prompt_sustained_sec", 3.2))

        # prune alarms older than window
        self._alarm_history = [t for t in self._alarm_history if (now - t) <= window_sec]
        self._alarm_history.append(now)

        if len(self._alarm_history) >= alarm_count:
            # frequent alarms in short period
            self._sustained_timer.stop()
            self._prompt_hud.show_prompt("new sitting position?", theme="yellow", auto_hide_ms=0)
            self.dimmer._keep_huds_on_top()
        else:
            # check if slouch is held for sustained duration
            self._sustained_timer.start(max(100, int(sustained_sec * 1000)))

    def _handle_slouch_ended(self):
        self._sustained_timer.stop()
        if self._prompt_hud.msg_lbl.text() == "new sitting position?":
            self._prompt_hud.hide()

    def _on_sustained_slouch(self):
        if self._was_slouching:
            self._prompt_hud.show_prompt("new sitting position?", theme="yellow", auto_hide_ms=0)
            self.dimmer._keep_huds_on_top()

    @Slot()
    def _on_prompt_pause_requested(self):
        self._alarm_history.clear()
        self._sustained_timer.stop()
        self._prompt_hud.hide()
        self.dimmer.set_dimmed(False)
        self._was_slouching = False
        self._tag_slouch_start = 0.0
        self.tray.set_paused(True)
        self.tray.showMessage(
            "slouchd paused",
            "monitoring paused. click the tray icon to resume.",
            SlouchdTrayIcon.MessageIcon.Information,
            3000
        )

    @Slot()
    def trigger_shortcut_calibration(self):
        self._alarm_history.clear()
        self._sustained_timer.stop()
        self._prompt_hud.hide()
        self.dimmer.set_dimmed(False)
        self._was_slouching = False
        self._tag_slouch_start = 0.0
        self._last_welcome_shown_time = time.time()
        self._startup_welcome_pending = False
        self._user_was_away = False

        source = self.config.get("perception_source", "tag")
        if source == "tag" and not self._tag_connected:
            self._calib_hud.show_error("tag not connected")
            return

        self._calibrating = True
        self._calib_samples.clear()
        if source == "camera":
            self.camera_worker.set_paused(False)
            self.camera_worker.set_preview_mode(True)

        self._calib_hud.show_progress(0, "calibrating posture...")

    def _finalize_shortcut_calibration(self):
        self._calibrating = False
        self._alarm_history.clear()
        self._sustained_timer.stop()
        self._prompt_hud.hide()
        self._was_slouching = False
        self._tag_slouch_start = 0.0
        self.dimmer.set_dimmed(False)
        self._calib_cooldown_until = time.time() + 1.2
        self._last_welcome_shown_time = time.time()
        self._startup_welcome_pending = False
        self._user_was_away = False
        source = self.config.get("perception_source", "tag")
        if source == "tag":
            avg_pitch = sum(self._calib_samples) / float(len(self._calib_samples))
            self.config.set("tag_baseline_pitch", float(avg_pitch))
            self.config.set("tag_calibrated", True)
            self.ble_worker.calibrate()
            self.tray.update_status(is_calibrated=True, is_slouching=False, user_present=bool(self._tag_connected))
        else:
            n = float(len(self._calib_samples))
            baseline = {
                "calibrated": True,
                "ear_shoulder_dist": float(sum(s["ear_shoulder_dist"] for s in self._calib_samples) / n),
                "nose_shoulder_dist": float(sum(s.get("nose_shoulder_dist", 0) for s in self._calib_samples) / n),
                "normalized_ear_shoulder": float(sum(s["normalized_ear_shoulder"] for s in self._calib_samples) / n),
                "shoulder_width": float(sum(s["shoulder_width"] for s in self._calib_samples) / n),
                "inter_ear_dist": float(sum(s["inter_ear_dist"] for s in self._calib_samples) / n)
            }
            self.config.set("baseline", baseline)
            is_calib_visible = bool(self.main_window.isVisible() and self.main_window.tabs.currentIndex() == 0)
            if not is_calib_visible:
                self.camera_worker.set_preview_mode(False)
                self.camera_worker.set_paused(self.tray.is_paused)
            self.tray.update_status(is_calibrated=True, is_slouching=False, user_present=True)

        self._calib_hud.show_done("posture calibrated")

    def _is_calibrated(self) -> bool:
        source = self.config.get("perception_source", "tag")
        if source == "tag":
            return bool(self.config.get("tag_calibrated", False))
        else:
            baseline = self.config.get("baseline", {})
            return bool(baseline.get("calibrated", False))

    def _get_windows_idle_seconds(self) -> float:
        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import Structure, c_uint, sizeof, byref
                class LASTINPUTINFO(Structure):
                    _fields_ = [('cbSize', c_uint), ('dwTime', c_uint)]
                lii = LASTINPUTINFO()
                lii.cbSize = sizeof(LASTINPUTINFO)
                if ctypes.windll.user32.GetLastInputInfo(byref(lii)):
                    millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
                    return max(0.0, float(millis) / 1000.0)
            except Exception:
                pass
        return 0.0

    def _show_welcome_back(self):
        if not self._is_calibrated():
            return
        if self._calibrating:
            return
        now = time.time()
        cooldown_sec = float(self.config.get("welcome_back_cooldown_sec", 30.0))
        away_threshold = float(self.config.get("welcome_back_away_sec", 120.0))
        effective_cooldown = min(cooldown_sec, away_threshold)
        if (now - self._last_welcome_shown_time) < effective_cooldown:
            return
        if self._was_slouching:
            return
        self._last_welcome_shown_time = now
        timeout_sec = float(self.config.get("welcome_back_hud_timeout_sec", 10.0))
        auto_hide_ms = max(0, int(timeout_sec * 1000))
        self._prompt_hud.show_prompt("welcome back. wanna?", theme="green", auto_hide_ms=auto_hide_ms)
        self.dimmer._keep_huds_on_top()

    def _check_user_presence(self):
        now = time.time()
        away_threshold = float(self.config.get("welcome_back_away_sec", 120.0))

        # detect sleep resume or timer gap
        tick_gap = now - self._last_presence_tick
        self._last_presence_tick = now
        if tick_gap >= away_threshold:
            self._user_was_away = True

        # check startup welcome pending
        if self._startup_welcome_pending:
            source = self.config.get("perception_source", "tag")
            if source == "tag":
                if self._tag_connected and self._latest_tag_data is not None:
                    self._startup_welcome_pending = False
                    self._show_welcome_back()
                    return
            else:
                idle = self._get_windows_idle_seconds()
                if idle < 4.0 and (now - self._last_user_active_time) > 2.5:
                    self._startup_welcome_pending = False
                    self._show_welcome_back()
                    return

        # check windows user input idle
        idle_sec = self._get_windows_idle_seconds()
        if idle_sec >= away_threshold:
            self._user_was_away = True
        elif idle_sec < 4.0:
            if self._user_was_away:
                self._user_was_away = False
                self._show_welcome_back()
            self._last_user_active_time = now

    @Slot()
    def open_calibration(self):
        self.open_window("calibrate")

    @Slot()
    def open_settings(self):
        self.open_window("settings")

    def open_window(self, tab: str = "calibrate"):
        source = self.config.get("perception_source", "tag")
        self.main_window.set_source(source)
        if source == "camera" and tab.lower() in ("calibrate", "calibration", "posture"):
            self.camera_worker.set_paused(False)
            self.camera_worker.set_preview_mode(True)
        self.main_window.show_tab(tab)

    def on_camera_preview_needed(self, needed: bool):
        if self.config.get("perception_source", "tag") == "camera":
            if self._calibrating:
                self.camera_worker.set_preview_mode(True)
                self.camera_worker.set_paused(False)
            else:
                self.camera_worker.set_preview_mode(needed)
                self.camera_worker.set_paused(self.tray.is_paused if not needed else False)

    @Slot(dict)
    def on_settings_changed(self, new_settings: dict):
        if "perception_source" in new_settings:
            new_source = new_settings.get("perception_source", "tag")
            self.apply_perception_source(new_source)

        if "tag_threshold_deg" in new_settings:
            self.ble_worker.set_threshold(float(new_settings["tag_threshold_deg"]))

        if "tag_vibration_mode" in new_settings:
            self.ble_worker.set_vibration_mode(int(new_settings["tag_vibration_mode"]))

        if "audio_sound" in new_settings:
            self._init_audio()

    @Slot(bool)
    def on_pause_toggled(self, is_paused):
        source = self.config.get("perception_source", "tag")
        if source == "tag":
            self.ble_worker.set_paused(is_paused)
            self.camera_worker.set_paused(True)
        else:
            self.camera_worker.set_paused(is_paused)
            self.ble_worker.set_paused(True)

        if is_paused:
            self.dimmer.set_dimmed(False)
            if self._was_slouching:
                self._handle_slouch_ended()

    def exit_app(self):
        if hasattr(self, "_presence_timer"):
            self._presence_timer.stop()
        self.hotkey.close()
        self._calib_hud.close()
        self._prompt_hud.close()
        self.dimmer.set_dimmed(False)
        self.tray.hide()
        self.ble_worker.stop()
        self.camera_worker.stop()
        self.ble_worker.wait(1000)
        self.camera_worker.wait(1000)
        self.app.quit()

    def run(self):
        return self.app.exec()

# ensure only one instance runs at a time
_single_instance_mutex = None

def acquire_single_instance_lock() -> bool:
    global _single_instance_mutex
    if sys.platform == "win32":
        import ctypes
        ERROR_ALREADY_EXISTS = 183
        mutex_name = "Local\\slouchd_singleton_mutex"
        kernel32 = ctypes.windll.kernel32
        _single_instance_mutex = kernel32.CreateMutexW(None, False, mutex_name)
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            return False
    return True

def main():
    setup_logging()
    if not acquire_single_instance_lock():
        print("slouchd is already running. exiting duplicate instance.")
        sys.exit(0)

    try:	# auto register startup in hkcu on launch (no admin needed)
        set_startup_enabled(True)
    except Exception as e:
        print(f"could not auto-register startup: {e}")

    app = SlouchdApp()
    sys.exit(app.run())

if __name__ == "__main__":
    main()
