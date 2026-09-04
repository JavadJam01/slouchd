import json
import re
import urllib.request
from PySide6.QtCore import Qt, Signal, QThread, QUrl, QObject, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtGui import QFont, QDesktopServices

def parse_version_tuple(v_str: str) -> tuple:
    """extract integer parts from version string like 'v0.1.0' -> (0, 1, 0)"""
    nums = [int(n) for n in re.findall(r'\d+', v_str)]
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)

class PeriodicUpdateChecker(QObject):
    update_available = Signal(dict)

    def __init__(self, current_version: str, repo: str = "JavadJam01/slouchd", interval_hours: int = 12, parent=None):
        super().__init__(parent)
        self.current_version = current_version
        self.repo = repo
        self._worker = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.check_now)
        interval_ms = max(1, interval_hours) * 60 * 60 * 1000
        self._timer.setInterval(interval_ms)

    def start(self, initial_delay_sec: int = 15):
        """starts periodic checking with a delay after app startup"""
        self._timer.start()
        if initial_delay_sec > 0:
            QTimer.singleShot(initial_delay_sec * 1000, self.check_now)

    def check_now(self):
        if self._worker is not None and self._worker.isRunning():
            return
        self._worker = UpdateCheckWorker(self.current_version, self.repo, self)
        self._worker.check_finished.connect(self._on_check_finished)
        self._worker.start()

    def _on_check_finished(self, res: dict):
        if res.get("status") == "success" and res.get("has_update"):
            self.update_available.emit(res)

class UpdateCheckWorker(QThread):
    check_finished = Signal(dict)

    def __init__(self, current_version: str, repo: str = "JavadJam01/slouchd", parent=None):
        super().__init__(parent)
        self.current_version = current_version
        self.repo = repo

    def run(self):
        result = {
            "status": "success",
            "has_update": False,
            "current_version": self.current_version,
            "latest_version": self.current_version,
            "release_name": "",
            "release_notes": "",
            "download_url": f"https://github.com/{self.repo}/releases/latest",
            "release_url": f"https://github.com/{self.repo}/releases/latest",
            "error_msg": ""
        }

        # 1. attempt github rest api
        api_url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        api_req = urllib.request.Request(
            api_url,
            headers={
                "User-Agent": "slouchd-desktop",
                "Accept": "application/vnd.github.v3+json"
            }
        )

        try:
            with urllib.request.urlopen(api_req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                latest_tag = data.get("tag_name", "").strip()
                if latest_tag:
                    result["latest_version"] = latest_tag.lstrip("v")
                    result["release_name"] = data.get("name", latest_tag)
                    result["release_notes"] = data.get("body", "")
                    result["release_url"] = data.get("html_url", result["release_url"])

                    # locate installer executable asset
                    assets = data.get("assets", [])
                    exe_asset = next(
                        (a for a in assets if a.get("name", "").lower().endswith(".exe")),
                        None
                    )
                    if exe_asset:
                        result["download_url"] = exe_asset.get("browser_download_url", result["release_url"])
                    else:
                        result["download_url"] = result["release_url"]

                    cur_tuple = parse_version_tuple(self.current_version)
                    latest_tuple = parse_version_tuple(result["latest_version"])
                    result["has_update"] = latest_tuple > cur_tuple
                    self.check_finished.emit(result)
                    return
        except Exception:
            # api failed or was rate limited, fall back to web redirect
            pass

        # 2. fallback: inspect http redirect on github.com/{repo}/releases/latest
        web_url = f"https://github.com/{self.repo}/releases/latest"
        web_req = urllib.request.Request(
            web_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )

        try:
            with urllib.request.urlopen(web_req, timeout=6) as response:
                final_url = response.geturl()
                if "/tag/" in final_url:
                    latest_tag = final_url.split("/tag/")[-1].strip("/")
                    clean_latest = latest_tag.lstrip("v")
                    result["latest_version"] = clean_latest
                    result["release_name"] = f"slouchd {latest_tag}"
                    result["release_url"] = final_url
                    clean_tag = latest_tag if latest_tag.startswith("v") else f"v{latest_tag}"
                    result["download_url"] = f"https://github.com/{self.repo}/releases/download/{latest_tag}/slouchd-setup-{clean_tag}.exe"

                    cur_tuple = parse_version_tuple(self.current_version)
                    latest_tuple = parse_version_tuple(clean_latest)
                    result["has_update"] = latest_tuple > cur_tuple
                    self.check_finished.emit(result)
                    return
                else:
                    # redirected to /releases without tag, repo has no published releases yet
                    result["has_update"] = False
                    self.check_finished.emit(result)
                    return
        except Exception as e:
            result["status"] = "error"
            result["error_msg"] = str(e)
            self.check_finished.emit(result)


class UpdateDialog(QDialog):
    def __init__(self, current_version: str, repo: str = "JavadJam01/slouchd", preloaded_result: dict = None, parent=None):
        super().__init__(parent)
        self.current_version = current_version
        self.repo = repo
        self.download_url = f"https://github.com/{self.repo}/releases/latest"
        self.release_url = f"https://github.com/{self.repo}/releases/latest"

        self.setWindowTitle("slouchd updates")
        self.setFixedSize(420, 240)
        self.setStyleSheet("""
            QDialog {
                background-color: #121216;
                color: #E4E4E7;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QLabel {
                color: #E4E4E7;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                font-weight: 600;
                font-size: 13px;
                padding: 8px 18px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #EF4444;
            }
            QPushButton#btn_secondary {
                background-color: #27272A;
                color: #D1D5DB;
            }
            QPushButton#btn_secondary:hover {
                background-color: #3F3F46;
                color: #FFFFFF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # header
        header_layout = QHBoxLayout()
        self.title_label = QLabel("check for updates")
        self.title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #F4F4F5;")

        self.version_badge = QLabel(f"v{self.current_version}")
        self.version_badge.setStyleSheet(
            "color: #A1A1AA; font-size: 12px; font-weight: 600; background: #27272A; padding: 2px 8px; border-radius: 4px;"
        )
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.version_badge)
        layout.addLayout(header_layout)

        # content card
        self.card = QFrame(self)
        self.card.setStyleSheet("background-color: #18181B; border: 1px solid #27272A; border-radius: 8px;")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(6)

        self.status_headline = QLabel("checking for updates...")
        self.status_headline.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self.status_headline.setStyleSheet("color: #E4E4E7; border: none; background: transparent;")

        self.status_detail = QLabel("connecting to github...")
        self.status_detail.setStyleSheet("color: #71717A; font-size: 12px; border: none; background: transparent;")
        self.status_detail.setWordWrap(True)

        card_layout.addWidget(self.status_headline)
        card_layout.addWidget(self.status_detail)
        layout.addWidget(self.card)

        # bottom buttons
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(10)
        self.button_layout.addStretch()

        self.btn_secondary = QPushButton("cancel", self)
        self.btn_secondary.setObjectName("btn_secondary")
        self.btn_secondary.clicked.connect(self.reject)

        self.btn_primary = QPushButton("ok", self)
        self.btn_primary.setVisible(False)
        self.btn_primary.clicked.connect(self.accept)

        self.button_layout.addWidget(self.btn_secondary)
        self.button_layout.addWidget(self.btn_primary)
        layout.addLayout(self.button_layout)

        self.worker = None
        if preloaded_result:
            self.on_check_finished(preloaded_result)
        else:
            self.worker = UpdateCheckWorker(self.current_version, self.repo, self)
            self.worker.check_finished.connect(self.on_check_finished)
            self.worker.start()

    def on_check_finished(self, res: dict):
        if res.get("status") == "error":
            self.status_headline.setText("unable to check for updates")
            self.status_headline.setStyleSheet("color: #EF4444; border: none; background: transparent;")
            self.status_detail.setText("could not reach github. check your network connection.")
            self.btn_secondary.setText("close")
            self.btn_primary.setText("open releases")
            self.btn_primary.setVisible(True)
            self.btn_primary.clicked.disconnect()
            self.btn_primary.clicked.connect(self._open_releases)
            return

        self.download_url = res.get("download_url", self.download_url)
        self.release_url = res.get("release_url", self.release_url)

        if res.get("has_update"):
            latest = res.get("latest_version")
            self.status_headline.setText(f"update available: v{latest}")
            self.status_headline.setStyleSheet("color: #4ADE80; font-weight: bold; border: none; background: transparent;")
            self.status_detail.setText(
                "a new version is available. download the installer to update slouchd."
            )
            self.btn_secondary.setText("later")
            self.btn_primary.setText("download installer")
            self.btn_primary.setVisible(True)
            self.btn_primary.clicked.disconnect()
            self.btn_primary.clicked.connect(self._download_update)
        else:
            self.status_headline.setText("you're up to date")
            self.status_headline.setStyleSheet("color: #F4F4F5; font-weight: bold; border: none; background: transparent;")
            self.status_detail.setText(f"slouchd v{self.current_version} is currently the newest version.")
            self.btn_secondary.setVisible(False)
            self.btn_primary.setText("ok")
            self.btn_primary.setVisible(True)
            self.btn_primary.clicked.disconnect()
            self.btn_primary.clicked.connect(self.accept)

    def _download_update(self):
        QDesktopServices.openUrl(QUrl(self.download_url))
        self.accept()

    def _open_releases(self):
        QDesktopServices.openUrl(QUrl(self.release_url))
        self.accept()

    def done(self, r):
        if hasattr(self, "worker") and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(1000)
        super().done(r)
