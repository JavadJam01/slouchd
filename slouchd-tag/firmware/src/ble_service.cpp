#include "ble_service.h"
#include "posture_engine.h"
#include "storage.h"
#include "imu_sensor.h"
#include "battery.h"

BleServiceManager Ble;

class ServerCallbacks : public NimBLEServerCallbacks {
    void onConnect(NimBLEServer* pServer, NimBLEConnInfo& connInfo) override {
        Ble.setConnected(true);
        Serial.printf("[ble] connected: %s\n", connInfo.getAddress().toString().c_str());
    }

    void onDisconnect(NimBLEServer* pServer, NimBLEConnInfo& connInfo, int reason) override {
        Ble.setConnected(false);
        Serial.printf("[ble] disconnected (0x%02x), advertising...\n", reason);
        NimBLEDevice::startAdvertising();
    }
};

class CommandCallbacks : public NimBLECharacteristicCallbacks {
    void onWrite(NimBLECharacteristic* pCharacteristic, NimBLEConnInfo& connInfo) override {
        std::string val = pCharacteristic->getValue();
        if (val.empty()) return;

        uint8_t cmd = static_cast<uint8_t>(val[0]);
        Serial.printf("[ble cmd] 0x%02x\n", cmd);

        switch (cmd) {
            case 0x01:	// calibrate baseline
                Posture.calibrate(Imu.getFilteredPitch(), Imu.getFilteredRoll());
                break;

            case 0x02:	// set threshold: [0x02, threshold_x10]
                if (val.size() >= 3) {
                    int16_t thresh_x10 = (int16_t)((uint8_t)val[1] | ((uint8_t)val[2] << 8));
                    Storage.saveThreshold((float)thresh_x10 / 10.0f);
                }
                break;

            case 0x03:	// set vibration mode: [0x03, mode]
                if (val.size() >= 2) {
                    Storage.saveVibrationMode(static_cast<uint8_t>(val[1]));
                }
                break;

            case 0x04:	// reset calibration
                Posture.reset();
                break;

            default:
                Serial.printf("[ble cmd] unknown 0x%02x\n", cmd);
                break;
        }
    }
};

static ServerCallbacks serverCallbacks;
static CommandCallbacks cmdCallbacks;

BleServiceManager::BleServiceManager()
    : _pServer(nullptr), _pDataChar(nullptr), _pCmdChar(nullptr), _pBatChar(nullptr),
      _isConnected(false), _packetSeq(0), _lastNotifiedBatPct(255) {}

void BleServiceManager::begin() {
    uint8_t mac[6];
    esp_read_mac(mac, ESP_MAC_BT);
    char devName[32];
    snprintf(devName, sizeof(devName), "slouchd-tag-%02X%02X", mac[4], mac[5]);

    NimBLEDevice::init(devName);
    NimBLEDevice::setPower(ESP_PWR_LVL_N0);	// 0 dbm tx power

    _pServer = NimBLEDevice::createServer();
    _pServer->setCallbacks(&serverCallbacks);

    NimBLEService* pService = _pServer->createService(SERVICE_UUID);	// custom posture telemetry service

    _pDataChar = pService->createCharacteristic(
        CHAR_DATA_UUID,
        NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
    );

    _pCmdChar = pService->createCharacteristic(
        CHAR_CMD_UUID,
        NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_NR
    );
    _pCmdChar->setCallbacks(&cmdCallbacks);

    pService->start();

    NimBLEService* pBatService = _pServer->createService(BLE_BATTERY_SERVICE_UUID);	// standard ble battery service (0x180F)
    _pBatChar = pBatService->createCharacteristic(
        BLE_BATTERY_LEVEL_CHAR_UUID,
        NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
    );
    uint8_t initBat = Battery.getBatteryPct();
    _pBatChar->setValue(&initBat, 1);
    pBatService->start();

    NimBLEAdvertising* pAdv = NimBLEDevice::getAdvertising();
    pAdv->setName(devName);
    pAdv->addServiceUUID(SERVICE_UUID);
    pAdv->addServiceUUID(BLE_BATTERY_SERVICE_UUID);
    pAdv->enableScanResponse(true);
    pAdv->setMinInterval(160);	// 100ms
    pAdv->setMaxInterval(320);	// 200ms
    pAdv->start();

    Serial.printf("[ble] advertising as %s\n", devName);
}

void BleServiceManager::sendTelemetry(float pitch, float roll, float baseline, float delta, bool isSlouching, bool isCalibrated) {
    if (!_isConnected || !_pServer || _pServer->getConnectedCount() == 0) return;

    uint8_t batPct = Battery.getBatteryPct();

    PostureTelemetryPacket packet;
    packet.pitch_x10    = (int16_t)roundf(pitch * 10.0f);
    packet.roll_x10     = (int16_t)roundf(roll * 10.0f);
    packet.baseline_x10 = (int16_t)roundf(baseline * 10.0f);
    packet.delta_x10    = (int16_t)roundf(delta * 10.0f);
    packet.is_slouching = isSlouching ? 1 : 0;
    packet.battery_pct  = batPct;
    packet.flags        = (isCalibrated ? 0x01 : 0x00) | (Battery.isLowBattery() ? 0x02 : 0x00);
    packet.seq          = _packetSeq++;

    _pDataChar->setValue(reinterpret_cast<const uint8_t*>(&packet), sizeof(packet));
    _pDataChar->notify();

    if (_pBatChar && batPct != _lastNotifiedBatPct) {
        _lastNotifiedBatPct = batPct;
        _pBatChar->setValue(&batPct, 1);
        _pBatChar->notify();
    }
}
