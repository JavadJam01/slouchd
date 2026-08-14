#include "haptics.h"

HapticsEngine Haptics;

HapticsEngine::HapticsEngine()
    : _activePattern(PATTERN_NONE), _startTime(0) {}

void HapticsEngine::begin() {
    pinMode(VIBRATOR_PIN, OUTPUT);
    digitalWrite(VIBRATOR_PIN, LOW);
}

void HapticsEngine::play(HapticPattern pattern) {
    _activePattern = pattern;
    _startTime = millis();
    digitalWrite(VIBRATOR_PIN, HIGH);
}

void HapticsEngine::stop() {
    _activePattern = PATTERN_NONE;
    digitalWrite(VIBRATOR_PIN, LOW);
}

void HapticsEngine::update(uint32_t /* now */) {
    uint32_t t = millis();	// read current time to prevent underflow

    if (_activePattern == PATTERN_NONE) {
        digitalWrite(VIBRATOR_PIN, LOW);
        return;
    }

    uint32_t elapsed = t - _startTime;

    switch (_activePattern) {
        case PATTERN_BOOT:
            if (elapsed >= 150) {	// 150ms pulse
                stop();
            } else {
                digitalWrite(VIBRATOR_PIN, HIGH);
            }
            break;

        case PATTERN_CALIBRATE:
            if (elapsed < 80) {	// double chirp pattern
                digitalWrite(VIBRATOR_PIN, HIGH);
            } else if (elapsed < 140) {
                digitalWrite(VIBRATOR_PIN, LOW);
            } else if (elapsed < 220) {
                digitalWrite(VIBRATOR_PIN, HIGH);
            } else {
                stop();
            }
            break;

        case PATTERN_SLOUCH_ALERT:
            if (elapsed < 220) {	// slouch alert pattern
                digitalWrite(VIBRATOR_PIN, HIGH);
            } else if (elapsed < 340) {
                digitalWrite(VIBRATOR_PIN, LOW);
            } else if (elapsed < 560) {
                digitalWrite(VIBRATOR_PIN, HIGH);
            } else {
                stop();
            }
            break;

        default:
            stop();
            break;
    }
}
