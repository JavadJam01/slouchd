#pragma once

#include "config.h"
#include <Arduino.h>

enum HapticPattern : uint8_t {
  PATTERN_NONE = 0,
  PATTERN_BOOT,	// boot buzz
  PATTERN_CALIBRATE,	// calibration buzz
  PATTERN_SLOUCH_ALERT	// slouch buzz
};

class HapticsEngine {
public:
  HapticsEngine();
  void begin();
  void play(HapticPattern pattern);
  void update(uint32_t now);
  void stop();
  bool isPlaying() const { return _activePattern != PATTERN_NONE; }
  HapticPattern getActivePattern() const { return _activePattern; }

private:
  HapticPattern _activePattern;
  uint32_t _startTime;
};

extern HapticsEngine Haptics;
