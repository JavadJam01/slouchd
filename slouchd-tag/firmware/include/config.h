#pragma once

#include <Arduino.h>

#define I2C_SDA_PIN 2	// esp32 c3 supermini wiring
#define I2C_SCL_PIN 3
#define I2C_FREQ_HZ 400000
#define VIBRATOR_PIN 7
#define BATTERY_ADC_PIN 0

#define BATTERY_DIVIDER_R1_OHMS 100000.0f	// battery voltage divider and sensing constants (100k + 100k to GPIO0)
#define BATTERY_DIVIDER_R2_OHMS 100000.0f
#define BATTERY_DIVIDER_RATIO ((BATTERY_DIVIDER_R1_OHMS + BATTERY_DIVIDER_R2_OHMS) / BATTERY_DIVIDER_R2_OHMS)	// 2.0
#define BATTERY_CALIBRATION_FACTOR 1.0f
#define BATTERY_SAMPLE_INTERVAL_MS 30000	// sampling battery percent every 30s
#define BATTERY_LOW_THRESHOLD_PCT 15

#define SERVICE_UUID "19B10000-E8F2-537E-4F6C-D104768A1214"	// ble uuids
#define CHAR_DATA_UUID "19B10001-E8F2-537E-4F6C-D104768A1214"
#define CHAR_CMD_UUID "19B10002-E8F2-537E-4F6C-D104768A1214"
#define BLE_BATTERY_SERVICE_UUID (uint16_t)0x180F
#define BLE_BATTERY_LEVEL_CHAR_UUID (uint16_t)0x2A19

#pragma pack(push, 1)	// telemetry packet format (12 bytes and little endian)
struct PostureTelemetryPacket {
  int16_t pitch_x10;	// pitch in 0.1 deg
  int16_t roll_x10;	// roll in 0.1 deg
  int16_t baseline_x10;	// baseline pitch in 0.1 deg
  int16_t delta_x10;	// pitch delta in 0.1 deg
  uint8_t is_slouching;	// 1=slouching, 0=upright
  uint8_t battery_pct;	// battery pct (0-100)
  uint8_t flags;	// bit 0: calibrated
  uint8_t seq;	// sequence number
};
#pragma pack(pop)

#define DEFAULT_SLOUCH_THRESHOLD_DEG 8.0f	// posture and timing constants: forward tilt threshold in degrees
#define MIN_THRESHOLD_DEG 2.0f
#define MAX_THRESHOLD_DEG 45.0f

#define SENSOR_SAMPLE_INTERVAL_MS 50	// imu sample rate (20 hz)
#define BLE_NOTIFY_INTERVAL_MS 100	// ble stream rate (10 hz)
#define SERIAL_LOG_INTERVAL_MS 500	// serial log rate (2 hz)

#define SLOUCH_DEBOUNCE_MS 300	// posture debounce time in ms
#define HAPTIC_GRACE_PERIOD_MS 1500	// grace period before vibration
#define HAPTIC_REPEAT_INTERVAL_MS 4000	// alert repeat interval

enum VibrationMode : uint8_t {	// vibration modes
  VIBE_DISABLED = 0,
  VIBE_STANDALONE_ONLY = 1,	// vibrate only when disconnected from laptop ble
  VIBE_ALWAYS = 2	// vibrate on every slouch
};
