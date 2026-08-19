#include "posture_engine.h"
#include "haptics.h"

PostureEngine Posture;

PostureEngine::PostureEngine()
    : _isCalibrated(false), _baselinePitch(0.0f), _baselineRoll(0.0f),
      _pitchDelta(0.0f), _instantSlouch(false), _currentSlouchState(false),
      _debounceStartTime(0), _slouchSustainStartTime(0),
      _lastHapticTriggerTime(0), _autoTaredOnBoot(false) {}

void PostureEngine::begin() {
  _isCalibrated = false;
}

void PostureEngine::calibrate(float currentPitch, float currentRoll) {
  _baselinePitch = currentPitch;
  _baselineRoll = currentRoll;
  _isCalibrated = true;
  _pitchDelta = 0.0f;
  Haptics.play(PATTERN_CALIBRATE);
}

void PostureEngine::reset() {
  _isCalibrated = false;
}

void PostureEngine::update(float currentPitch, float currentRoll, bool isBleConnected) {
  uint32_t now = millis();
  if (!_autoTaredOnBoot && now >= 2000) {
    _autoTaredOnBoot = true;
    calibrate(currentPitch, currentRoll);
  }
  _pitchDelta = _isCalibrated ? (_baselinePitch - currentPitch) : 0.0f;
  _instantSlouch = _isCalibrated && (_pitchDelta > 8.0f);
  if (_instantSlouch) {
    if (_slouchSustainStartTime == 0) _slouchSustainStartTime = now;
    else if (now - _slouchSustainStartTime >= 1500) {
      if (_lastHapticTriggerTime == 0 || (now - _lastHapticTriggerTime >= 4000)) {
        _lastHapticTriggerTime = now;
        Haptics.play(PATTERN_SLOUCH_ALERT);
      }
    }
  } else {
    _slouchSustainStartTime = 0;
    _lastHapticTriggerTime = 0;
  }
}
