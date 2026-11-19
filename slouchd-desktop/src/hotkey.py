import sys
import shutil
import subprocess
import ast
import atexit
from PySide6.QtCore import Signal, Slot, ClassInfo, QObject
from PySide6.QtWidgets import QWidget

if sys.platform != "win32":
    from PySide6.QtDBus import QDBusConnection

    @ClassInfo(**{"D-Bus Interface": "org.slouchd.App"})
    class _SlouchdDBusAdaptor(QObject):
        def __init__(self, callback, parent=None):
            super().__init__(parent)
            self._callback = callback

        @Slot()
        def Recalibrate(self):
            self._callback()


class GlobalHotkey(QWidget):
    """registers global hotkey across platforms (ctrl+alt+c)"""
    activated = Signal()

    def __init__(self, modifiers: int = 0x4003, vk_code: int = 0x43, hotkey_id: int = 101, parent=None):
        super().__init__(parent)
        self.hotkey_id = hotkey_id
        self._registered = False
        self._gnome_registered = False

        if sys.platform == "win32":
            import ctypes
            self._user32 = ctypes.windll.user32
            # ctrl+alt+c without repeat
            self._registered = bool(self._user32.RegisterHotKey(int(self.winId()), self.hotkey_id, modifiers, vk_code))
        else:
            self._init_linux()

    def _init_linux(self):
        try:
            self._dbus_adaptor = _SlouchdDBusAdaptor(self.activated.emit, self)
            bus = QDBusConnection.sessionBus()
            bus.registerObject("/org/slouchd/App", self._dbus_adaptor, QDBusConnection.RegisterOption.ExportAllSlots)
            bus.registerService("org.slouchd.App")
            self._register_desktop_keybinding()
            atexit.register(self.close)
        except Exception as e:
            print(f"could not init linux global hotkey: {e}")

    def _register_desktop_keybinding(self):
        if shutil.which("gsettings") is None:
            return
        cmd = "gdbus call --session --dest org.slouchd.App --object-path /org/slouchd/App --method org.slouchd.App.Recalibrate"
        schemas = [
            ("org.gnome.settings-daemon.plugins.media-keys", "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/slouchd/"),
            ("org.cinnamon.desktop.keybindings", "/org/cinnamon/desktop/keybindings/custom-keybindings/slouchd/"),
            ("org.mate.SettingsDaemon.plugins.media-keys", "/org/mate/settings-daemon/plugins/media-keys/custom-keybindings/slouchd/"),
        ]
        for base_schema, path in schemas:
            try:
                check = subprocess.run(["gsettings", "get", base_schema, "custom-keybindings"], capture_output=True, text=True)
                if check.returncode != 0:
                    continue
                custom_schema = f"{base_schema}.custom-keybinding:{path}"
                subprocess.run(["gsettings", "set", custom_schema, "name", "slouchd recalibrate"], check=True, capture_output=True)
                subprocess.run(["gsettings", "set", custom_schema, "command", cmd], check=True, capture_output=True)
                subprocess.run(["gsettings", "set", custom_schema, "binding", "<Control><Alt>c"], check=True, capture_output=True)

                out = check.stdout.strip()
                try:
                    bindings = ast.literal_eval(out)
                except Exception:
                    bindings = []
                if path not in bindings:
                    bindings.append(path)
                    subprocess.run(["gsettings", "set", base_schema, "custom-keybindings", str(bindings)], check=True, capture_output=True)

                self._registered_schema = (base_schema, path, custom_schema)
                self._gnome_registered = True
                break
            except Exception:
                continue

    def _unregister_desktop_keybinding(self):
        if not getattr(self, "_gnome_registered", False) or not hasattr(self, "_registered_schema"):
            return
        try:
            base_schema, path, custom_schema = self._registered_schema
            check = subprocess.run(["gsettings", "get", base_schema, "custom-keybindings"], capture_output=True, text=True)
            if check.returncode == 0:
                try:
                    bindings = ast.literal_eval(check.stdout.strip())
                except Exception:
                    bindings = []
                if path in bindings:
                    bindings.remove(path)
                    subprocess.run(["gsettings", "set", base_schema, "custom-keybindings", str(bindings)], check=True, capture_output=True)
            subprocess.run(["gsettings", "reset-recursively", custom_schema], capture_output=True)
            self._gnome_registered = False
        except Exception:
            pass

    def nativeEvent(self, eventType, message):
        if sys.platform == "win32" and self._registered:
            from ctypes import wintypes
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0312 and msg.wParam == self.hotkey_id:
                self.activated.emit()
                return True, 0
        return super().nativeEvent(eventType, message)

    def close(self):
        if sys.platform == "win32" and self._registered:
            self._user32.UnregisterHotKey(int(self.winId()), self.hotkey_id)
            self._registered = False
        elif sys.platform != "win32":
            self._unregister_desktop_keybinding()
            try:
                bus = QDBusConnection.sessionBus()
                bus.unregisterService("org.slouchd.App")
                bus.unregisterObject("/org/slouchd/App")
            except Exception:
                pass
        super().close()
