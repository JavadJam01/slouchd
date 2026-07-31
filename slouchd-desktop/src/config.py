import json
import os
import sys
import tempfile
import threading
from pathlib import Path

def get_resource_path(relative_path: str = "") -> Path:
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    return (base / relative_path) if relative_path else base

DEFAULT_CONFIG = {
    "perception_source": "camera",
    "camera_index": 0,
    "dim_opacity": 0.65,
    "grace_period_sec": 1.0,
    "sensitivity": 1.0,
    "check_interval_sec": 1.0,
    "baseline": {
        "calibrated": False,
        "ear_shoulder_dist": 0.0,
        "nose_shoulder_dist": 0.0,
        "inter_ear_dist": 0.0,
        "shoulder_width": 0.0,
    }
}

def get_app_dir() -> Path:
    candidates = []
    if os.name == "nt" and "LOCALAPPDATA" in os.environ:
        candidates.append(Path(os.environ["LOCALAPPDATA"]) / "slouchd")
    elif "XDG_CONFIG_HOME" in os.environ:
        candidates.append(Path(os.environ["XDG_CONFIG_HOME"]) / "slouchd")
    else:
        candidates.append(Path.home() / ".config" / "slouchd")
    candidates.append(Path(__file__).resolve().parent.parent / ".data")
    candidates.append(Path(tempfile.gettempdir()) / "slouchd")

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except (OSError, PermissionError):
            continue
    return Path(tempfile.gettempdir()) / "slouchd"

class ConfigManager:
    def __init__(self):
        self._lock = threading.RLock()
        self.config_path = get_app_dir() / "config.json"
        self._data = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        with self._lock:
            if self.config_path.exists():
                try:
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        self._data.update(json.load(f))
                except Exception:
                    pass

    def save(self):
        with self._lock:
            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, indent=2)
            except Exception:
                pass

    def get(self, key, default=None):
        with self._lock:
            return self._data.get(key, default)

    def set(self, key, value):
        with self._lock:
            self._data[key] = value
            self.save()
