#include "imu_sensor.h"
#include <math.h>

ImuSensor Imu;

ImuSensor::ImuSensor()
    : _imu(Wire, 0), _isHealthy(false), _firstSample(true),
      _filteredPitch(0.0f), _filteredRoll(0.0f), _rawPitch(0.0f),
      _rawRoll(0.0f) {}

bool ImuSensor::begin() {
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, I2C_FREQ_HZ);

  int ret = _imu.begin();
  if (ret != 0) {
    Serial.printf("[imu] 0x68 failed (%d), trying 0x69...\n", ret);
    _imu = ICM42670(Wire, 1);
    ret = _imu.begin();
  }

  if (ret == 0) {
    _imu.startAccel(25, 2);	// low power mode: accelerometer only at 25 hz, ±2g range (gyro off)
    _isHealthy = true;
    Serial.println("[imu] initialized (25hz accel)");
    return true;
  } else {
    _isHealthy = false;
    Serial.printf("[imu] init failed (%d)\n", ret);
    return false;
  }
}

bool ImuSensor::update() {
  if (!_isHealthy)
    return false;

  inv_imu_sensor_event_t event;
  int ret = _imu.getDataFromRegisters(event);
  if (ret != 0)
    return false;

  float ax = (float)event.accel[0] / 16384.0f;	// full scale +-2g (16384 lsb/g)
  float ay = (float)event.accel[1] / 16384.0f;
  float az = (float)event.accel[2] / 16384.0f;

  _rawPitch = atan2f(az, sqrtf(ax * ax + ay * ay)) * (180.0f / (float)M_PI);	// collar axis mapping: x=lateral, y=vertical, z=forward
  _rawRoll = atan2f(ax, sqrtf(ay * ay + az * az)) * (180.0f / (float)M_PI);

  const float alpha = 0.25f;	// low pass filter (alpha = 0.25)
  if (_firstSample) {
    _filteredPitch = _rawPitch;
    _filteredRoll = _rawRoll;
    _firstSample = false;
  } else {
    _filteredPitch = alpha * _rawPitch + (1.0f - alpha) * _filteredPitch;
    _filteredRoll = alpha * _rawRoll + (1.0f - alpha) * _filteredRoll;
  }

  return true;
}
