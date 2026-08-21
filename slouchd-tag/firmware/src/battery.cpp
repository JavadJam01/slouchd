#include "battery.h"
#include "haptics.h"

BatteryMonitor Battery;

struct SocPoint {	// empirical state of charge curve for 1s 3.7v lipo (500mah or 600mah (i guess it doesnt matter)) with 100k + 100k voltage divider to gpio0
    uint16_t mv;
    uint8_t pct;
};

static const SocPoint SOC_TABLE[] = {
    {3300, 0},
    {3500, 5},
    {3600, 10},
    {3650, 15},
    {3700, 20},
    {3730, 30},
    {3770, 40},
    {3820, 50},
    {3880, 60},
    {3950, 70},
    {4030, 80},
    {4100, 90},
    {4150, 95},
    {4200, 100}
};
static const size_t SOC_TABLE_SIZE = sizeof(SOC_TABLE) / sizeof(SOC_TABLE[0]);

BatteryMonitor::BatteryMonitor()
    : _voltageMv(0), _batteryPct(100), _lastSampleTime(0), _filteredPinMv(0.0f) {}

void BatteryMonitor::begin() {
    pinMode(BATTERY_ADC_PIN, INPUT);
    analogSetPinAttenuation(BATTERY_ADC_PIN, ADC_11db);

    uint32_t sum = 0;	// initial burst reading to establish baseline filter state immediately
    const uint8_t INIT_SAMPLES = 32;
    for (uint8_t i = 0; i < INIT_SAMPLES; ++i) {
        sum += analogReadMilliVolts(BATTERY_ADC_PIN);
        delayMicroseconds(200);
    }

    _filteredPinMv = (float)sum / (float)INIT_SAMPLES;
    _voltageMv = (uint16_t)roundf(_filteredPinMv * BATTERY_DIVIDER_RATIO * BATTERY_CALIBRATION_FACTOR);
    _batteryPct = calculatePercentage(_voltageMv);
    _lastSampleTime = millis();

    Serial.printf("[battery] initialized: GPIO %d, raw pin: %.1f mV, bat: %u mV (%u%%)\n",
                  BATTERY_ADC_PIN, _filteredPinMv, _voltageMv, _batteryPct);
}

uint16_t BatteryMonitor::readPinMillivolts() {
    uint32_t sum = 0;
    const uint8_t SAMPLES = 16;
    for (uint8_t i = 0; i < SAMPLES; ++i) {
        sum += analogReadMilliVolts(BATTERY_ADC_PIN);
        delayMicroseconds(150);
    }
    return (uint16_t)(sum / SAMPLES);
}

void BatteryMonitor::update(uint32_t now) {
    if (now - _lastSampleTime < BATTERY_SAMPLE_INTERVAL_MS) {
        return;
    }

    if (Haptics.isPlaying()) {	// defer reading if the vibration motor is active
        return;
    }

    _lastSampleTime = now;

    uint16_t rawPinMv = readPinMillivolts();

    if (_filteredPinMv <= 0.1f) {	// exponential moving average filter to smooth adc noise and load transients
        _filteredPinMv = (float)rawPinMv;
    } else {
        _filteredPinMv = (0.85f * _filteredPinMv) + (0.15f * (float)rawPinMv);
    }

    _voltageMv = (uint16_t)roundf(_filteredPinMv * BATTERY_DIVIDER_RATIO * BATTERY_CALIBRATION_FACTOR);
    _batteryPct = calculatePercentage(_voltageMv);
}

uint8_t BatteryMonitor::calculatePercentage(uint16_t mv) {
    if (mv >= SOC_TABLE[SOC_TABLE_SIZE - 1].mv) {
        return 100;
    }
    if (mv <= SOC_TABLE[0].mv) {
        return 0;
    }

    for (size_t i = 0; i < SOC_TABLE_SIZE - 1; ++i) {
        if (mv >= SOC_TABLE[i].mv && mv <= SOC_TABLE[i + 1].mv) {
            uint16_t vLow = SOC_TABLE[i].mv;
            uint16_t vHigh = SOC_TABLE[i + 1].mv;
            uint8_t pLow = SOC_TABLE[i].pct;
            uint8_t pHigh = SOC_TABLE[i + 1].pct;

            float fraction = (float)(mv - vLow) / (float)(vHigh - vLow);
            return (uint8_t)roundf((float)pLow + fraction * (float)(pHigh - pLow));
        }
    }

    return 0;
}
