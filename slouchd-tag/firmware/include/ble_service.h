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

    void setConnected(bool connected) { _isConnected = connected; }

private:
    NimBLEServer* _pServer;
    NimBLECharacteristic* _pDataChar;
    NimBLECharacteristic* _pCmdChar;
    NimBLECharacteristic* _pBatChar;
    bool _isConnected;
    uint8_t _packetSeq;
    uint8_t _lastNotifiedBatPct;
};

extern BleServiceManager Ble;
