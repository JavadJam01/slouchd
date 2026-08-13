#pragma once

#include <Arduino.h>
#include <Wire.h>
#include "ICM42670P.h"
#include "config.h"

class ImuSensor {
public:
    ImuSensor();
    bool begin();
    bool update();

    float getFilteredPitch() const { return _filteredPitch; }
    float getFilteredRoll() const { return _filteredRoll; }
    float getRawPitch() const { return _rawPitch; }
    float getRawRoll() const { return _rawRoll; }
    bool isHealthy() const { return _isHealthy; }

private:
    ICM42670 _imu;
    bool _isHealthy;
    bool _firstSample;
    float _filteredPitch;
    float _filteredRoll;
    float _rawPitch;
    float _rawRoll;
};

extern ImuSensor Imu;
