#pragma once

#include <Arduino.h>
#include "config.h"

class PostureEngine {
public:
    PostureEngine();
    void begin();
    void update(float currentPitch, float currentRoll, bool isBleConnected);

    void calibrate(float currentPitch, float currentRoll);
    void reset();

    bool isCalibrated() const { return _isCalibrated; }
    float getBaselinePitch() const { return _baselinePitch; }
    float getBaselineRoll() const { return _baselineRoll; }
    float getPitchDelta() const { return _pitchDelta; }
    bool isSlouching() const { return _currentSlouchState; }
    bool isInstantSlouching() const { return _instantSlouch; }

private:
    bool _isCalibrated;
    float _baselinePitch;
    float _baselineRoll;
    float _pitchDelta;
    bool _instantSlouch;
    bool _currentSlouchState;

    uint32_t _debounceStartTime;
    uint32_t _slouchSustainStartTime;
    uint32_t _lastHapticTriggerTime;
    bool _autoTaredOnBoot;
};

extern PostureEngine Posture;
