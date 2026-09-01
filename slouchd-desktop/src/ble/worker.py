import sys
import asyncio
import struct
import threading
from PySide6.QtCore import QThread, Signal, Slot

SERVICE_UUID = "19b10000-e8f2-537e-4f6c-d104768a1214"
CHAR_DATA_UUID = "19b10001-e8f2-537e-4f6c-d104768a1214"
CHAR_CMD_UUID = "19b10002-e8f2-537e-4f6c-d104768a1214"

class BleTagWorker(QThread):
    """ble worker for slouchd-tag"""
    tag_connected = Signal(bool, str)	# (is_connected, device_name)
    tag_data = Signal(dict)	# {pitch, roll, baseline_pitch, delta, is_slouching, battery, calibrated, seq}
    tag_battery = Signal(int)	# battery percentage (0-100)
    tag_status = Signal(str)	# status message for ui
    tag_error = Signal(str)	# error message

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self._running = True
        self._is_paused = False
        self._loop = None
        self._cmd_queue = None
        self._last_battery = -1
        self._client = None
        self._is_connected = False

    def run(self):
        try:
            import bleak
        except ImportError:
            self.tag_error.emit("bleak library not found")
            self.tag_status.emit("ble library missing")
            print("ble worker: bleak not installed")
            return

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._cmd_queue = asyncio.Queue()

        try:
            self._loop.run_until_complete(self._main_ble_loop())
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"ble worker fatal error: {e}")
            self.tag_error.emit(f"ble worker error: {e}")
        finally:
            self._loop.close()

    async def _main_ble_loop(self):
        from bleak import BleakScanner, BleakClient

        while self._running:
            if self._is_paused:
                await asyncio.sleep(0.5)
                continue

            target_name = self.config.get("tag_name", "slouchd-tag")
            target_mac = self.config.get("tag_mac", "").strip()

            self.tag_status.emit("scanning for tag...")
            print(f"scanning for {target_name}...")

            device = None
            try:
                if target_mac:
                    device = await BleakScanner.find_device_by_address(target_mac, timeout=4.0)
                
                if not device:
                    devices = await BleakScanner.discover(timeout=4.0, service_uuids=[SERVICE_UUID])	# scan by service uuid
                    if devices:
                        device = devices[0]
                    else:
                        all_devs = await BleakScanner.discover(timeout=3.0)	# fallback: check all discovered names for any match
                        for d in all_devs:
                            if d.name and (target_name.lower() in d.name.lower() or "slouchd" in d.name.lower()):
                                device = d
                                break
            except Exception as e:
                err_text = str(e).lower()
                print(f"scan error: {e}")
                if "off" in err_text or "adapter" in err_text or "power" in err_text or "disabled" in err_text:
                    self.tag_error.emit("bluetooth is off")
                    self.tag_status.emit("bluetooth is off")
                else:
                    self.tag_error.emit(f"scan error: {e}")
                await asyncio.sleep(3.0)
                continue

            if not device or not self._running:
                self.tag_status.emit("tag not found, retrying...")
                await asyncio.sleep(3.0)
                continue

            dev_name = device.name or "slouchd-tag"
            print(f"connecting to {dev_name}...")
            self.tag_status.emit(f"connecting to {dev_name}...")

            def disconnected_callback(client):
                print(f"device {dev_name} disconnected")
                self._is_connected = False
                self.tag_connected.emit(False, "")
                self.tag_status.emit("tag disconnected")

            try:
                async with BleakClient(device, disconnected_callback=disconnected_callback, timeout=10.0) as client:
                    self._client = client
                    print(f"connected to {dev_name}")

                    await asyncio.sleep(0.3)	# wait for gatt discovery

                    self._is_connected = True
                    self.tag_connected.emit(True, dev_name)
                    self.tag_status.emit(f"connected to {dev_name}")

                    def notification_handler(sender, data: bytearray):
                        if len(data) >= 12:
                            try:
                                (pitch_x10, roll_x10, base_x10, delta_x10,
                                 is_slouch, bat, flags, seq) = struct.unpack('<hhhhBBBB', data[:12])

                                pitch = pitch_x10 / 10.0
                                roll = roll_x10 / 10.0
                                baseline = base_x10 / 10.0
                                delta = delta_x10 / 10.0
                                is_slouching = bool(is_slouch)
                                calibrated = bool(flags & 0x01)

                                self.tag_data.emit({
                                    "pitch": pitch,
                                    "roll": roll,
                                    "baseline_pitch": baseline,
                                    "delta": delta,
                                    "is_slouching": is_slouching,
                                    "battery": bat,
                                    "calibrated": calibrated,
                                    "seq": seq,
                                    "source": "tag"
                                })

                                if bat != self._last_battery:
                                    self._last_battery = bat
                                    self.tag_battery.emit(bat)
                            except Exception as ex:
                                print(f"error unpacking packet: {ex}")

                    print("subscribing to ble notifications...")
                    await client.start_notify(CHAR_DATA_UUID, notification_handler)
                    print("streaming ble telemetry")

                    thresh = float(self.config.get("tag_threshold_deg", 8.0))	# sync threshold if configured
                    try:
                        thresh_payload = struct.pack('<Bh', 0x02, int(thresh * 10))
                        await client.write_gatt_char(CHAR_CMD_UUID, thresh_payload, response=False)
                    except Exception as ex:
                        print(f"initial threshold sync error: {ex}")

                    vib_mode = int(self.config.get("tag_vibration_mode", 1))	# sync vibration mode on connect so tag matches desktop setting
                    try:
                        await client.write_gatt_char(CHAR_CMD_UUID, bytes([0x03, vib_mode]), response=False)
                        print(f"synced vibration mode: {vib_mode}")
                    except Exception as ex:
                        print(f"initial vibration sync error: {ex}")

                    while self._running and client.is_connected:	# process commands
                        try:
                            cmd_item = await asyncio.wait_for(self._cmd_queue.get(), timeout=0.2)	# wait for commands from ui thread
                            cmd_type = cmd_item[0]

                            if cmd_type == "calibrate":
                                print("sending calibrate command")
                                await client.write_gatt_char(CHAR_CMD_UUID, bytes([0x01]), response=False)
                                self.tag_status.emit("tag calibrated")
                            elif cmd_type == "set_threshold":
                                thresh_val = cmd_item[1]
                                print(f"sending threshold: {thresh_val}")
                                payload = struct.pack('<Bh', 0x02, int(thresh_val * 10))
                                await client.write_gatt_char(CHAR_CMD_UUID, payload, response=False)
                            elif cmd_type == "set_vibration_mode":
                                mode_val = int(cmd_item[1])
                                print(f"sending vibration mode: {mode_val}")
                                await client.write_gatt_char(CHAR_CMD_UUID, bytes([0x03, mode_val]), response=False)
                            elif cmd_type == "reset":
                                print("sending reset command")
                                await client.write_gatt_char(CHAR_CMD_UUID, bytes([0x04]), response=False)
                                self.tag_status.emit("tag calibration reset")

                            self._cmd_queue.task_done()
                        except asyncio.TimeoutError:
                            pass
                        except Exception as e:
                            print(f"command error: {e}")
                            self.tag_error.emit(f"command error: {e}")

                    try:
                        await client.stop_notify(CHAR_DATA_UUID)
                    except Exception:
                        pass

            except Exception as e:
                print(f"connection error: {e}")
                self._is_connected = False
                self.tag_error.emit(f"connection error: {e}")
                self.tag_connected.emit(False, "")
                self.tag_status.emit("connection lost, reconnecting...")
            finally:
                self._client = None
                self._is_connected = False
                self.tag_connected.emit(False, "")

            await asyncio.sleep(2.0)

    @property
    def is_connected(self) -> bool:
        """does the tag currently connected via ble?"""
        return self._is_connected

    def calibrate(self):
        """send calibration command to the tag"""
        if self._loop and self._cmd_queue:
            self._loop.call_soon_threadsafe(self._cmd_queue.put_nowait, ("calibrate",))

    def set_threshold(self, threshold_deg: float):
        """update slouch threshold on the tag."""
        if self._loop and self._cmd_queue:
            self._loop.call_soon_threadsafe(self._cmd_queue.put_nowait, ("set_threshold", threshold_deg))

    def set_vibration_mode(self, mode: int):
        """update vibration mode on the tag."""
        if self._loop and self._cmd_queue:
            self._loop.call_soon_threadsafe(self._cmd_queue.put_nowait, ("set_vibration_mode", mode))

    def reset_calibration(self):
        """reset posture baseline on the tag."""
        if self._loop and self._cmd_queue:
            self._loop.call_soon_threadsafe(self._cmd_queue.put_nowait, ("reset",))

    def set_paused(self, paused: bool):
        self._is_paused = paused

    def stop(self):
        self._running = False
        if self._loop and self._cmd_queue:
            self._loop.call_soon_threadsafe(self._cmd_queue.put_nowait, ("stop",))
