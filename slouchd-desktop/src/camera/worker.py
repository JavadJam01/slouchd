import os
import time
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal, Slot, QMutex, QMutexLocker, QWaitCondition
from PySide6.QtGui import QImage
from src.posture.detector import PostureDetector

class CameraWorker(QThread):
    frame_ready = Signal(object, dict, bool, float)
    status_changed = Signal(str)
    camera_error = Signal(str)

    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self._running = False
        self._paused = False
        self._preview_mode = False
        self._mutex = QMutex()
        self._wait_cond = QWaitCondition()
        self.detector = None

    def stop(self):
        with QMutexLocker(self._mutex):
            self._running = False
            self._wait_cond.wakeAll()

    def set_paused(self, paused: bool):
        with QMutexLocker(self._mutex):
            self._paused = paused
            self._wait_cond.wakeAll()

    def set_preview_mode(self, enabled: bool):
        with QMutexLocker(self._mutex):
            self._preview_mode = enabled
            self._wait_cond.wakeAll()

    def _open_capture(self, cam_idx):
        cap = None
        if os.name == 'nt':
            cap = cv2.VideoCapture(cam_idx, cv2.CAP_MSMF)	# native windows media foundation preserves natural aspect ratio and color planes
            if not cap or not cap.isOpened():
                cap = cv2.VideoCapture(cam_idx)
            if not cap or not cap.isOpened():
                cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(cam_idx)

        if cap and cap.isOpened():
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass
        return cap

    def run(self):
        with QMutexLocker(self._mutex):
            self._running = True

        current_cam_idx = self.config.get("camera_index", 0)
        cap = None
        failed_reads = 0
        camera_error_emitted = False

        if self.detector is None:
            try:
                self.detector = PostureDetector()
            except Exception as e:
                print(f"detector init error: {e}")
                self.camera_error.emit(f"detector init failed: {e}")

        slouch_start_time = None
        last_slouch_seen = None
        last_user_seen = time.time()
        is_confirmed_slouching = False

        while True:
            with QMutexLocker(self._mutex):
                if not self._running:
                    break
                is_paused = self._paused
                is_preview = self._preview_mode

            if is_paused and not is_preview:	# release camera when paused
                if cap is not None:
                    cap.release()
                    cap = None
                    self.status_changed.emit("camera released")
                    slouch_start_time = None
                    last_slouch_seen = None
                    is_confirmed_slouching = False
                    failed_reads = 0
                    camera_error_emitted = False

                with QMutexLocker(self._mutex):
                    if not self._running:
                        break
                    if self._paused and not self._preview_mode:
                        self._wait_cond.wait(self._mutex, 250)
                continue

            configured_cam = self.config.get("camera_index", 0)	# reopen camera if changed, resuming, or previously lost
            if cap is None or not cap.isOpened() or configured_cam != current_cam_idx:
                if cap is not None:
                    cap.release()
                    cap = None
                current_cam_idx = configured_cam
                cap = self._open_capture(current_cam_idx)
                if not cap or not cap.isOpened():
                    if not camera_error_emitted:
                        self.camera_error.emit(f"cannot open camera {current_cam_idx}")
                        camera_error_emitted = True
                    cap = None
                    with QMutexLocker(self._mutex):
                        if not self._running:
                            break
                        self._wait_cond.wait(self._mutex, 1000)
                    continue
                self.status_changed.emit("camera active")
                failed_reads = 0
                camera_error_emitted = False

            if not is_preview:	# flush old frames in background mode
                for _ in range(3):
                    if not cap.grab():
                        break

            ret, frame = cap.read()
            is_corrupt_frame = False
            if ret and frame is not None:
                if frame.size == 0 or frame.mean() < 0.8:	# detect solid black or empty frame if stream was hijacked/blocked
                    is_corrupt_frame = True

            if not ret or frame is None or is_corrupt_frame:
                failed_reads += 1
                if failed_reads >= 3:
                    if not camera_error_emitted:
                        self.camera_error.emit("camera unavailable or in use by another app")
                        camera_error_emitted = True
                    if cap is not None:
                        cap.release()
                        cap = None
                with QMutexLocker(self._mutex):
                    if not self._running:
                        break
                    self._wait_cond.wait(self._mutex, 300)
                continue

            if failed_reads > 0 or camera_error_emitted:	# successfully read frame
                failed_reads = 0
                camera_error_emitted = False

            if is_preview:	# mirror frame for preview only
                frame = cv2.flip(frame, 1)

            metrics = None
            annotated_frame = None

            if self.detector:
                try:
                    metrics, annotated_frame = self.detector.process_frame(frame, annotate=is_preview)
                except Exception as ex:
                    print(f"process frame error: {ex}")

            baseline = self.config.get("baseline", {})
            sensitivity = self.config.get("sensitivity", 1.0)
            grace_period = self.config.get("grace_period_sec", 1.0)

            is_instant_slouching, slouch_ratio = False, 0.0
            now = time.time()

            user_present = bool(metrics and metrics.get("visibility", 0.0) >= 0.25)
            if user_present:
                last_user_seen = now

            if metrics and baseline.get("calibrated"):
                is_instant_slouching, slouch_ratio = self.detector.evaluate_slouch(
                    metrics, baseline, sensitivity
                )

                if is_instant_slouching:
                    if slouch_start_time is None:
                        slouch_start_time = now
                    last_slouch_seen = now
                    if (now - slouch_start_time) >= grace_period:
                        is_confirmed_slouching = True
                else:
                    slouch_start_time = None	# clear slouching when upright
                    last_slouch_seen = None
                    is_confirmed_slouching = False
            else:
                slouch_start_time = None	# clear slouching when no pose detected
                last_slouch_seen = None
                is_confirmed_slouching = False

            qimg = None
            if is_preview and annotated_frame is not None:
                rgb_frame = np.ascontiguousarray(cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB))	# convert annotated frame to contiguous qimage to avoid stride or memory distortion
                h, w, ch = rgb_frame.shape
                qimg = QImage(rgb_frame.data, w, h, rgb_frame.strides[0], QImage.Format_RGB888).copy()

            out_metrics = metrics if metrics is not None else {}
            self.frame_ready.emit(qimg, out_metrics, is_confirmed_slouching, slouch_ratio)

            if is_preview:
                with QMutexLocker(self._mutex):	# smooth 20 FPS for calibration preview
                    if not self._running:
                        break
                    if self._preview_mode:
                        self._wait_cond.wait(self._mutex, 50)
            elif is_confirmed_slouching:
                with QMutexLocker(self._mutex):	# balanced 2.8 Hz (350ms) adaptive sampling while dimmed for instant recovery detection with low CPU
                    if not self._running:
                        break
                    if not self._preview_mode and not self._paused:
                        self._wait_cond.wait(self._mutex, 350)
            elif (now - last_user_seen) > 30.0:
                with QMutexLocker(self._mutex):	# if user is away for > 30s; sleep for 2.5s for power saving
                    if not self._running:
                        break
                    if not self._preview_mode and not self._paused:
                        self._wait_cond.wait(self._mutex, 2500)
            else:
                interval_ms = int(float(self.config.get("check_interval_sec", 1.0)) * 1000)	# ultra low power background sampling (default 1.0s / 1 Hz)
                with QMutexLocker(self._mutex):
                    if not self._running:
                        break
                    if not self._preview_mode and not self._paused:
                        self._wait_cond.wait(self._mutex, max(100, interval_ms))

        if cap is not None:
            cap.release()
            cap = None
        if self.detector:
            try:
                self.detector.close()
            except Exception:
                pass
            self.detector = None
        self.status_changed.emit("camera stopped")
