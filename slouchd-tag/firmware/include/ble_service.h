#pragma once
#include <Arduino.h>
#include <NimBLEDevice.h>
#include "config.h"

class BleServiceManager {
public:
    BleServiceManager();
    void begin();
    void sendTelemetry(float pitch, float roll, float baseline, float delta, bool isSlouching, bool isCalibrated);
    bool isConnected() const { return _isConnected; }
    void setConnected(bool c) { _isConnected = c; }
private:
    NimBLEServer* _pServer;
    NimBLECharacteristic* _pDataChar;
    bool _isConnected;
    uint8_t _packetSeq;
};

extern BleServiceManager Ble;
