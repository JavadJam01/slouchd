import time
import cv2
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker, QWaitCondition
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
        self._mutex = QMutex()
        self._wait_cond = QWaitCondition()
        self.detector = PostureDetector()

    def run(self):
        with QMutexLocker(self._mutex):
            self._running = True
        cap = cv2.VideoCapture(self.config.get("camera_index", 0))
        while True:
            with QMutexLocker(self._mutex):
                if not self._running:
                    break
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.1)
                continue
            metrics, _ = self.detector.process_frame(frame, annotate=False)
            baseline = self.config.get("baseline", {})
            is_slouching, ratio = False, 0.0
            if metrics and baseline.get("calibrated"):
                is_slouching, ratio = self.detector.evaluate_slouch(metrics, baseline)
            self.frame_ready.emit(None, metrics or {}, is_slouching, ratio)
            time.sleep(float(self.config.get("check_interval_sec", 1.0)))
        cap.release()

    def stop(self):
        with QMutexLocker(self._mutex):
            self._running = False
            self._wait_cond.wakeAll()
