import sys
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

class GlobalHotkey(QWidget):
    """registers global hotkey on windows (ctrl+alt+c)"""
    activated = Signal()

    def __init__(self, modifiers: int = 0x4003, vk_code: int = 0x43, hotkey_id: int = 101, parent=None):
        super().__init__(parent)
        self.hotkey_id = hotkey_id
        self._registered = False
        if sys.platform == "win32":
            import ctypes
            self._user32 = ctypes.windll.user32
            # ctrl+alt+c without repeat
            self._registered = bool(self._user32.RegisterHotKey(int(self.winId()), self.hotkey_id, modifiers, vk_code))

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
        super().close()
