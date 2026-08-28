import sys
import asyncio
import struct
from PySide6.QtCore import QThread, Signal

SERVICE_UUID = "19b10000-e8f2-537e-4f6c-d104768a1214"
CHAR_DATA_UUID = "19b10001-e8f2-537e-4f6c-d104768a1214"
CHAR_CMD_UUID = "19b10002-e8f2-537e-4f6c-d104768a1214"

class BleTagWorker(QThread):
    tag_connected = Signal(bool, str)
    tag_data = Signal(dict)
    tag_battery = Signal(int)
    tag_status = Signal(str)
    tag_error = Signal(str)

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self._running = True
        self._is_paused = False
        self._is_connected = False
        self._loop = None
        self._cmd_queue = None

    def run(self):
        try:
            import bleak
        except ImportError:
            self.tag_error.emit("bleak library not found")
            return
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._cmd_queue = asyncio.Queue()
        try:
            self._loop.run_until_complete(self._main_loop())
        finally:
            self._loop.close()

    async def _main_loop(self):
        from bleak import BleakScanner, BleakClient
        while self._running:
            if self._is_paused:
                await asyncio.sleep(0.5)
                continue
            self.tag_status.emit("scanning for tag...")
            try:
                device = await BleakScanner.find_device_by_filter(
                    lambda d, ad: d.name and "slouchd" in d.name.lower(),
                    timeout=4.0
                )
                if not device:
                    await asyncio.sleep(2.0)
                    continue
                async with BleakClient(device) as client:
                    self._is_connected = True
                    self.tag_connected.emit(True, device.name or "slouchd-tag")
                    def on_data(sender, data):
                        if len(data) >= 12:
                            p, r, b, d, s, bat, fl, seq = struct.unpack('<hhhhBBBB', data[:12])
                            self.tag_data.emit({"pitch": p/10.0, "roll": r/10.0, "is_slouching": bool(s), "battery": bat})
                    await client.start_notify(CHAR_DATA_UUID, on_data)
                    while self._running and client.is_connected:
                        await asyncio.sleep(0.5)
            except Exception as e:
                self.tag_error.emit(str(e))
                await asyncio.sleep(2.0)

    @property
    def is_connected(self):
        return self._is_connected

    def calibrate(self):
        pass
    def set_threshold(self, th):
        pass
    def set_vibration_mode(self, m):
        pass
    def set_paused(self, p):
        self._is_paused = p
    def stop(self):
        self._running = False
