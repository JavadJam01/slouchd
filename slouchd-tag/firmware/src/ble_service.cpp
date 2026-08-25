#include "ble_service.h"
#include "battery.h"

BleServiceManager Ble;

class ServerCallbacks : public NimBLEServerCallbacks {
    void onConnect(NimBLEServer* pServer, NimBLEConnInfo& connInfo) override {
        Ble.setConnected(true);
    }
    void onDisconnect(NimBLEServer* pServer, NimBLEConnInfo& connInfo, int reason) override {
        Ble.setConnected(false);
        NimBLEDevice::startAdvertising();
    }
};

static ServerCallbacks serverCallbacks;

BleServiceManager::BleServiceManager()
    : _pServer(nullptr), _pDataChar(nullptr), _pCmdChar(nullptr), _pBatChar(nullptr),
      _isConnected(false), _packetSeq(0), _lastNotifiedBatPct(255) {}

void BleServiceManager::begin() {
    NimBLEDevice::init("slouchd-tag");
    _pServer = NimBLEDevice::createServer();
    _pServer->setCallbacks(&serverCallbacks);
    NimBLEService* pService = _pServer->createService(SERVICE_UUID);
    _pDataChar = pService->createCharacteristic(CHAR_DATA_UUID, NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY);
    pService->start();
    NimBLEAdvertising* pAdv = NimBLEDevice::getAdvertising();
    pAdv->setName("slouchd-tag");
    pAdv->addServiceUUID(SERVICE_UUID);
    pAdv->start();
}

void BleServiceManager::sendTelemetry(float pitch, float roll, float baseline, float delta, bool isSlouching, bool isCalibrated) {
    if (!_isConnected || !_pServer) return;
    PostureTelemetryPacket packet;
    packet.pitch_x10 = (int16_t)roundf(pitch * 10.0f);
    packet.roll_x10 = (int16_t)roundf(roll * 10.0f);
    packet.baseline_x10 = (int16_t)roundf(baseline * 10.0f);
    packet.delta_x10 = (int16_t)roundf(delta * 10.0f);
    packet.is_slouching = isSlouching ? 1 : 0;
    packet.battery_pct = Battery.getBatteryPct();
    packet.flags = isCalibrated ? 0x01 : 0x00;
    packet.seq = _packetSeq++;
    _pDataChar->setValue((const uint8_t*)&packet, sizeof(packet));
    _pDataChar->notify();
}
