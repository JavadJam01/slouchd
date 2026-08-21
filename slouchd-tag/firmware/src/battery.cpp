#include "battery.h"
#include "haptics.h"

BatteryMonitor Battery;

struct SocPoint {
    uint16_t mv;
    uint8_t pct;
};

static const SocPoint SOC_TABLE[] = {
    {3300, 0}, {3500, 5}, {3600, 10}, {3650, 15}, {3700, 20},
    {3730, 30}, {3770, 40}, {3820, 50}, {3880, 60}, {3950, 70},
    {4030, 80}, {4100, 90}, {4150, 95}, {4200, 100}
};
static const size_t SOC_TABLE_SIZE = sizeof(SOC_TABLE) / sizeof(SOC_TABLE[0]);

BatteryMonitor::BatteryMonitor()
    : _voltageMv(0), _batteryPct(100), _lastSampleTime(0), _filteredPinMv(0.0f) {}

void BatteryMonitor::begin() {
    pinMode(BATTERY_ADC_PIN, INPUT);
    analogSetPinAttenuation(BATTERY_ADC_PIN, ADC_11db);
    _lastSampleTime = millis();
}

uint16_t BatteryMonitor::readPinMillivolts() {
    return analogReadMilliVolts(BATTERY_ADC_PIN);
}

void BatteryMonitor::update(uint32_t now) {
    if (now - _lastSampleTime < 30000) return;
    _lastSampleTime = now;
    uint16_t raw = readPinMillivolts();
    _filteredPinMv = (float)raw;
    _voltageMv = (uint16_t)roundf(_filteredPinMv * 2.0f);
    _batteryPct = calculatePercentage(_voltageMv);
}

uint8_t BatteryMonitor::calculatePercentage(uint16_t mv) {
    if (mv >= 4200) return 100;
    if (mv <= 3300) return 0;
    return (uint8_t)((mv - 3300) * 100 / (4200 - 3300));
}
