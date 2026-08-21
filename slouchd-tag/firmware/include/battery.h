#pragma once
#include <Arduino.h>
#include "config.h"

class BatteryMonitor {
public:
    BatteryMonitor();
    void begin();
    void update(uint32_t now);
    uint8_t getBatteryPct() const { return _batteryPct; }
    uint16_t getVoltageMv() const { return _voltageMv; }
private:
    uint16_t _voltageMv;
    uint8_t _batteryPct;
    uint32_t _lastSampleTime;
    float _filteredPinMv;
    uint16_t readPinMillivolts();
    uint8_t calculatePercentage(uint16_t mv);
};

extern BatteryMonitor Battery;
