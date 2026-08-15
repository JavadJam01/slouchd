#include <Arduino.h>
#include "config.h"
#include "imu_sensor.h"
#include "haptics.h"

void setup() {
  setCpuFrequencyMhz(80);
  Serial.begin(115200);
  delay(200);
  Serial.println("[slouchd-tag] initializing");
  Haptics.begin();
  Imu.begin();
  Haptics.play(PATTERN_BOOT);
}

void loop() {
  uint32_t now = millis();
  Imu.update();
  Haptics.update(now);
  delay(50);
}
