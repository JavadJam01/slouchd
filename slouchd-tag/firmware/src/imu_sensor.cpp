#include "imu_sensor.h"

ImuSensor Imu;

ImuSensor::ImuSensor() : _imu(Wire, 0), _isHealthy(false), _firstSample(true),
  _filteredPitch(0.0f), _filteredRoll(0.0f), _rawPitch(0.0f), _rawRoll(0.0f) {}

bool ImuSensor::begin() {
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, I2C_FREQ_HZ);
  int ret = _imu.begin();
  if (ret != 0) {
    _imu = ICM42670(Wire, 1);
    ret = _imu.begin();
  }
  _isHealthy = (ret == 0);
  return _isHealthy;
}

bool ImuSensor::update() {
  return _isHealthy;
}
