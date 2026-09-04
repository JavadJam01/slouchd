import os
import sys
from pathlib import Path

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "slouchd"

def is_startup_enabled() -> bool:
    """checks if slouchd is set to run at windows startup"""
    if sys.platform != "win32":
        return False
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

def get_launch_command() -> str:
    """returns executable command to register in windows startup."""
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        return f'"{exe}"'
    else:	# fallback for running directly in dev
        python_exe = Path(sys.executable).resolve()
        main_py = (Path(__file__).resolve().parent / "main.py").resolve()
        return f'"{python_exe}" "{main_py}"'

def set_startup_enabled(enabled: bool) -> bool:
    """enables or disables slouchd startup on login without admin rights"""
    if sys.platform != "win32":
        return False
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
