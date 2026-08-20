#pragma once

#include <Arduino.h>
#include <Preferences.h>
#include "config.h"

class StorageManager {
public:
    StorageManager();
    void begin();
    
    bool isCalibrated() const { return _calibrated; }
    float getBaselinePitch() const { return _basePitch; }
    float getBaselineRoll() const { return _baseRoll; }
    float getThresholdDeg() const { return _thresholdDeg; }
    uint8_t getVibrationMode() const { return _vibrationMode; }

    void saveCalibration(float basePitch, float baseRoll);
    void resetCalibration();
    void saveThreshold(float threshDeg);
    void saveVibrationMode(uint8_t mode);

private:
    Preferences _prefs;
    bool _calibrated;
    float _basePitch;
    float _baseRoll;
    float _thresholdDeg;
    uint8_t _vibrationMode;
};

extern StorageManager Storage;
