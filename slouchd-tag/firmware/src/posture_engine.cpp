#include "posture_engine.h"
#include "haptics.h"
#include "storage.h"

PostureEngine Posture;

PostureEngine::PostureEngine()
    : _isCalibrated(false), _baselinePitch(0.0f), _baselineRoll(0.0f),
      _pitchDelta(0.0f), _instantSlouch(false), _currentSlouchState(false),
      _debounceStartTime(0), _slouchSustainStartTime(0),
      _lastHapticTriggerTime(0), _autoTaredOnBoot(false) {}

void PostureEngine::begin() {
  _isCalibrated = Storage.isCalibrated();
  _baselinePitch = Storage.getBaselinePitch();
  _baselineRoll = Storage.getBaselineRoll();
}

void PostureEngine::calibrate(float currentPitch, float currentRoll) {
  _baselinePitch = currentPitch;
  _baselineRoll = currentRoll;
  _isCalibrated = true;
  _pitchDelta = 0.0f;
  _instantSlouch = false;
  _currentSlouchState = false;
  _slouchSustainStartTime = 0;
  _lastHapticTriggerTime = 0;

  Storage.saveCalibration(_baselinePitch, _baselineRoll);
  Haptics.play(PATTERN_CALIBRATE);
  Serial.printf("[posture] calibrated -> pitch: %.1f, roll: %.1f\n",
                _baselinePitch, _baselineRoll);
}

void PostureEngine::reset() {
  _isCalibrated = false;
  _baselinePitch = 0.0f;
  _baselineRoll = 0.0f;
  _pitchDelta = 0.0f;
  _instantSlouch = false;
  _currentSlouchState = false;
  _slouchSustainStartTime = 0;
  _lastHapticTriggerTime = 0;

  Storage.resetCalibration();
}

void PostureEngine::update(float currentPitch, float currentRoll,
                           bool isBleConnected) {
  uint32_t now = millis();

  if (!_autoTaredOnBoot && now >= 2000) {	// auto-calibrate baseline after 2s
    _autoTaredOnBoot = true;
    calibrate(currentPitch, currentRoll);
    Serial.println("[posture] auto-calibrated baseline");
  }

  _pitchDelta = _isCalibrated ? (_baselinePitch - currentPitch) : 0.0f;	// forward slouch delta: pitch decreases as collar tilts forward

  float threshold = Storage.getThresholdDeg();
  _instantSlouch = _isCalibrated && (_pitchDelta > threshold);

  if (_instantSlouch != _currentSlouchState) {	// debounce state changes
    if (_debounceStartTime == 0) {
      _debounceStartTime = now;
    } else if (now - _debounceStartTime >= SLOUCH_DEBOUNCE_MS) {
      _currentSlouchState = _instantSlouch;
      _debounceStartTime = 0;
    }
  } else {
    _debounceStartTime = 0;
  }

  uint8_t vibMode = Storage.getVibrationMode();	// haptic alerting logic (using debounced state to avoid imu noise resetting the sustain timer)
  bool vibeAllowed = (vibMode == VIBE_ALWAYS) ||
                     (vibMode == VIBE_STANDALONE_ONLY && !isBleConnected);

  static uint32_t lastHapticDebug = 0;	// periodic debug log for haptic (every 2s while slouch detected)
  if (_instantSlouch && (now - lastHapticDebug >= 2000)) {
    lastHapticDebug = now;
    Serial.printf("[haptic dbg] cal=%d debounced=%d instant=%d vib_mode=%u "
                  "vibe_allowed=%d ble_conn=%d sustain=%lu\n",
                  _isCalibrated, _currentSlouchState, _instantSlouch, vibMode,
                  vibeAllowed, isBleConnected,
                  _slouchSustainStartTime ? (now - _slouchSustainStartTime)
                                          : 0UL);
  }

  if (_isCalibrated && _currentSlouchState && vibeAllowed) {
    if (_slouchSustainStartTime == 0) {
      _slouchSustainStartTime = now;
    } else {
      uint32_t sustainedMs = now - _slouchSustainStartTime;
      if (sustainedMs >= HAPTIC_GRACE_PERIOD_MS) {
        if (_lastHapticTriggerTime == 0 ||
            (now - _lastHapticTriggerTime >= HAPTIC_REPEAT_INTERVAL_MS)) {
          _lastHapticTriggerTime = now;
          Haptics.play(PATTERN_SLOUCH_ALERT);
          Serial.println("[posture] slouch confirmed, buzzing");
        }
      }
    }
  } else {
    _slouchSustainStartTime = 0;
    _lastHapticTriggerTime = 0;

    if (!_currentSlouchState &&	// stop slouch buzz when upright (but dont kill the boot/cal buzzes)
        Haptics.getActivePattern() == PATTERN_SLOUCH_ALERT) {
      Haptics.stop();
    }
  }
}
