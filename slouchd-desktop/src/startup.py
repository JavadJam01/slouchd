import os
import sys
from pathlib import Path

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "slouchd"


def _get_linux_autostart_file() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        base = Path(config_home)
    else:
        base = Path.home() / ".config"
    return base / "autostart" / f"{APP_NAME}.desktop"


def get_launch_command() -> str:
    """returns executable command to register in system startup."""
    # when packaged as AppImage, the host binary path is kept in $APPIMAGE
    appimage_path = os.environ.get("APPIMAGE")
    if appimage_path and os.path.exists(appimage_path):
        return f'"{appimage_path}"'

    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        return f'"{exe}"'
    else:	# fallback for running directly in dev
        python_exe = Path(sys.executable).resolve()
        main_py = (Path(__file__).resolve().parent / "main.py").resolve()
        return f'"{python_exe}" "{main_py}"'


def is_startup_enabled() -> bool:
    """checks if slouchd is set to run at login / startup"""
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, APP_NAME)
                return bool(value)
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"error checking startup registry: {e}")
            return False
    elif sys.platform.startswith("linux"):
        return _get_linux_autostart_file().is_file()

    return False


def set_startup_enabled(enabled: bool) -> bool:
    """enables or disables slouchd startup on login without admin rights"""
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
                if enabled:
                    cmd = get_launch_command()
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
            return True
        except Exception as e:
            print(f"error updating startup registry: {e}")
            return False
    elif sys.platform.startswith("linux"):
        try:
            desktop_file = _get_linux_autostart_file()
            if enabled:
                desktop_file.parent.mkdir(parents=True, exist_ok=True)
                raw_cmd = get_launch_command().strip('"')
                desktop_entry = (
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    "Version=1.0\n"
                    "Name=slouchd\n"
                    "GenericName=Posture Monitor\n"
                    "Comment=Gentle multi-screen slouch monitor\n"
                    f"Exec=\"{raw_cmd}\"\n"
                    "Icon=slouchd\n"
                    "Terminal=false\n"
                    "Categories=Utility;\n"
                    "StartupNotify=false\n"
                    "X-GNOME-Autostart-enabled=true\n"
                )
                desktop_file.write_text(desktop_entry, encoding="utf-8")
            else:
                if desktop_file.is_file():
                    desktop_file.unlink()
            return True
        except Exception as e:
            print(f"error updating linux autostart desktop entry: {e}")
            return False

    return False
