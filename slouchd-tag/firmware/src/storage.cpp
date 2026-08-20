#include "storage.h"

StorageManager Storage;

StorageManager::StorageManager()
    : _calibrated(false), _basePitch(0.0f), _baseRoll(0.0f),
      _thresholdDeg(DEFAULT_SLOUCH_THRESHOLD_DEG), _vibrationMode(VIBE_ALWAYS) {}

void StorageManager::begin() {
    _prefs.begin("slouchd", true);
    _calibrated = _prefs.getBool("calibrated", false);
    _basePitch = _prefs.getFloat("base_pitch", 0.0f);
    _baseRoll = _prefs.getFloat("base_roll", 0.0f);
    _thresholdDeg = _prefs.getFloat("thresh_deg", DEFAULT_SLOUCH_THRESHOLD_DEG);
    _vibrationMode = _prefs.getUChar("vib_mode", VIBE_ALWAYS);
    _prefs.end();

    if (_thresholdDeg < MIN_THRESHOLD_DEG || _thresholdDeg > MAX_THRESHOLD_DEG) {
        _thresholdDeg = DEFAULT_SLOUCH_THRESHOLD_DEG;
    }

    Serial.printf("[storage] loaded: calibrated=%d, base_pitch=%.1f, base_roll=%.1f, thresh=%.1f, vib_mode=%u\n",
                  _calibrated, _basePitch, _baseRoll, _thresholdDeg, _vibrationMode);
}

void StorageManager::saveCalibration(float basePitch, float baseRoll) {
    _calibrated = true;
    _basePitch = basePitch;
    _baseRoll = baseRoll;

    _prefs.begin("slouchd", false);
    _prefs.putBool("calibrated", _calibrated);
    _prefs.putFloat("base_pitch", _basePitch);
    _prefs.putFloat("base_roll", _baseRoll);
    _prefs.end();

    Serial.printf("[storage] saved calibration -> pitch: %.1f, roll: %.1f\n", _basePitch, _baseRoll);
}

void StorageManager::resetCalibration() {
    _calibrated = false;
    _basePitch = 0.0f;
    _baseRoll = 0.0f;

    _prefs.begin("slouchd", false);
    _prefs.putBool("calibrated", false);
    _prefs.putFloat("base_pitch", 0.0f);
    _prefs.putFloat("base_roll", 0.0f);
    _prefs.end();

    Serial.println("[storage] calibration reset");
}

void StorageManager::saveThreshold(float threshDeg) {
    if (threshDeg < MIN_THRESHOLD_DEG) threshDeg = MIN_THRESHOLD_DEG;
    if (threshDeg > MAX_THRESHOLD_DEG) threshDeg = MAX_THRESHOLD_DEG;
    _thresholdDeg = threshDeg;

    _prefs.begin("slouchd", false);
    _prefs.putFloat("thresh_deg", _thresholdDeg);
    _prefs.end();

    Serial.printf("[storage] saved threshold: %.1f\n", _thresholdDeg);
}

void StorageManager::saveVibrationMode(uint8_t mode) {
    if (mode > 2) mode = VIBE_ALWAYS;
    _vibrationMode = mode;

    _prefs.begin("slouchd", false);
    _prefs.putUChar("vib_mode", _vibrationMode);
    _prefs.end();

    Serial.printf("[storage] saved vibration mode: %u\n", _vibrationMode);
}
