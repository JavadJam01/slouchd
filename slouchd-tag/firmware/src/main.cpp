// slouchd-tag firmware

#include "battery.h"
#include "ble_service.h"
#include "config.h"
#include "haptics.h"
#include "imu_sensor.h"
#include "posture_engine.h"
#include "storage.h"
#include <Arduino.h>

void setup() {
  setCpuFrequencyMhz(80);	// underclock to 80 mhz for power saving

  Serial.begin(115200);
  delay(200);
  Serial.println("\n[slouchd-tag] initializing");

  Battery.begin();	// initialize subsystems
  Haptics.begin();
  Storage.begin();
  Imu.begin();
  Posture.begin();
  Ble.begin();

  Haptics.play(PATTERN_BOOT);	// boot buzz

  Serial.println("[slouchd-tag] ready");
}

void loop() {
  uint32_t now = millis();

  Battery.update(now);	// update battery monitor

  if (Imu.update()) {	// read and filter imu data
    float pitch = Imu.getFilteredPitch();
    float roll = Imu.getFilteredRoll();

    Posture.update(pitch, roll, Ble.isConnected());	// evaluate posture state

    static uint32_t lastBleNotify = 0;	// send ble telemetry at 10 hz
    if (now - lastBleNotify >= BLE_NOTIFY_INTERVAL_MS) {
      lastBleNotify = now;
      Ble.sendTelemetry(pitch, roll, Posture.getBaselinePitch(),
                        Posture.getPitchDelta(), Posture.isSlouching(),
                        Posture.isCalibrated());
    }

    static uint32_t lastSerialLog = 0;	// log diagnostics at 2 hz
    if (now - lastSerialLog >= SERIAL_LOG_INTERVAL_MS) {
      lastSerialLog = now;
      Serial.printf("[posture] pitch: %+.1f, base: %+.1f, delta: %+.1f, slouch: %s, bat: %u%% (%u mV), mode: %s\n",
                    pitch, Posture.getBaselinePitch(), Posture.getPitchDelta(),
                    Posture.isSlouching() ? "slouch" : "upright",
                    Battery.getBatteryPct(), Battery.getVoltageMv(),
                    Ble.isConnected() ? "connected" : "standalone");
    }
  }

  Haptics.update(now);	// update haptics

  delay(SENSOR_SAMPLE_INTERVAL_MS); // 20 hz loop delay
}