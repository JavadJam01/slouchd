#pragma once
#include <Arduino.h>

#define I2C_SDA_PIN 2
#define I2C_SCL_PIN 3
#define I2C_FREQ_HZ 400000
#define VIBRATOR_PIN 7
#define BATTERY_ADC_PIN 0

#define BATTERY_DIVIDER_RATIO 2.0f
#define BATTERY_CALIBRATION_FACTOR 1.0f
#define BATTERY_SAMPLE_INTERVAL_MS 30000

#define SERVICE_UUID "19B10000-E8F2-537E-4F6C-D104768A1214"
#define CHAR_DATA_UUID "19B10001-E8F2-537E-4F6C-D104768A1214"
#define CHAR_CMD_UUID "19B10002-E8F2-537E-4F6C-D104768A1214"
#define BLE_BATTERY_SERVICE_UUID (uint16_t)0x180F
#define BLE_BATTERY_LEVEL_CHAR_UUID (uint16_t)0x2A19

#pragma pack(push, 1)
struct PostureTelemetryPacket {
  int16_t pitch_x10;
  int16_t roll_x10;
  int16_t baseline_x10;
  int16_t delta_x10;
  uint8_t is_slouching;
  uint8_t battery_pct;
  uint8_t flags;
  uint8_t seq;
};
#pragma pack(pop)

#define DEFAULT_SLOUCH_THRESHOLD_DEG 8.0f
#define MIN_THRESHOLD_DEG 2.0f
#define MAX_THRESHOLD_DEG 45.0f

#define SENSOR_SAMPLE_INTERVAL_MS 50
#define BLE_NOTIFY_INTERVAL_MS 100
#define SERIAL_LOG_INTERVAL_MS 500

enum VibrationMode : uint8_t {
  VIBE_DISABLED = 0,
  VIBE_STANDALONE_ONLY = 1,
  VIBE_ALWAYS = 2
};
