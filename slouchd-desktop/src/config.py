import json
import os
import sys
import tempfile
import threading
from pathlib import Path

def get_resource_path(relative_path: str = "") -> Path:
    """returns absolute path to resource, working for dev and pyinstaller .exe"""
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
        target = (base / relative_path) if relative_path else base
        if target.exists() or not relative_path:
            return target

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        target = (exe_dir / relative_path) if relative_path else exe_dir
        if target.exists():
            return target
        target_internal = exe_dir / "_internal" / relative_path
        if target_internal.exists():
            return target_internal

    base = Path(__file__).resolve().parent.parent
    return (base / relative_path) if relative_path else base

DEFAULT_CONFIG = {
    "perception_source": "camera",	# "tag" or "camera"
    "tag_name": "slouchd-tag",
    "tag_mac": "",
    "tag_threshold_deg": 8.0,
    "tag_calibrated": False,
    "tag_baseline_pitch": 0.0,
    "tag_baseline_roll": 0.0,
    "tag_vibration_mode": 1,	# 0=disabled, 1=disconnected only, 2=always
    "camera_index": 0,
    "dim_opacity": 0.65,
    "grace_period_sec": 1.0,
    "sensitivity": 1.0,	# 0.5 to 1.5
    "check_interval_sec": 1.0,	# sampling interval in seconds
    "audio_alert": True,
    "audio_sound": "notification-1.wav",
    "baseline": {
        "calibrated": False,
        "ear_shoulder_dist": 0.0,
        "nose_shoulder_dist": 0.0,
        "inter_ear_dist": 0.0,
        "shoulder_width": 0.0,
    }
}

def get_app_dir() -> Path:
    """returns app data directory."""
    candidates = []
    if os.name == "nt" and "LOCALAPPDATA" in os.environ:
        candidates.append(Path(os.environ["LOCALAPPDATA"]) / "slouchd")
    elif "XDG_CONFIG_HOME" in os.environ:
        candidates.append(Path(os.environ["XDG_CONFIG_HOME"]) / "slouchd")
    else:
        candidates.append(Path.home() / ".config" / "slouchd")

    candidates.append(Path(__file__).resolve().parent.parent / ".data")	# fallback paths
    candidates.append(Path(tempfile.gettempdir()) / "slouchd")

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            test_file = candidate / ".write_test"	# verify write access
            test_file.touch(exist_ok=True)
            test_file.unlink(missing_ok=True)
            return candidate
        except (OSError, PermissionError):
            continue

    return Path(tempfile.gettempdir()) / "slouchd"

class ConfigManager:
    def __init__(self):
        self._lock = threading.RLock()
        app_dir = get_app_dir()
        self.config_path = app_dir / "config.json"
        self._data = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        with self._lock:
            if self.config_path.exists():
                try:
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        saved = json.load(f)
                        self._data.update(saved)
                except Exception as e:
                    print(f"error loading config, using default: {e}")

    def save(self):
        with self._lock:
            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, indent=2)
            except Exception as e:
                print(f"error saving config: {e}")

    def get(self, key, default=None):
        with self._lock:
            return self._data.get(key, default)

    def set(self, key, value):
        with self._lock:
            self._data[key] = value
            self.save()

    def update(self, new_dict):
        with self._lock:
            self._data.update(new_dict)
            self.save()
