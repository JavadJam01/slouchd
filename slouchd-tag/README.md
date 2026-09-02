# slouchd-tag

this is the firmware and hardware documentation for slouchd-tag, our opensource wearable posture tracking collar tag. you clip it to your shirt or collar and it tracks your posture via an imu sensor. it can talk to the desktop app over ble, or it can work in standalone mode when you are away from your desk and buzz you when you slouch.

## parts

here are the hardware parts we are using:

-  esp32 c3 SuperMini (risc-v 32-bit core, ble 5.0, super small form factor)
-  InvenSense icm-42670p (6-axis)
- **battery**:
  - cell: JSPCELL 702030 ~500mAh (or 600mAh, im not sure about it cause it was not clearly printed on mine but i think it does not really matter in our firmware so you can use any capacity that works for you) 3.7v 1s lipo
  - charger: tp4056 module (i replaced its programming resistor (r3) with a 3.9k resistor to reduce charging current from 1A to ~308 mA for increasing the battery lifespan)
  - switched 5v rail -> esp32 5v / vin pin
  - Battery sensing: 100k / 100k voltage devider connected to **gpio 0**
- coin vibration motor connected to **gpio 7** (for haptic buzz alerts)

### wiring
heres how everything is connected:

- sda to gpio 2
- scl to gpio 3
- vibrator to gpio 7 and its vcc to 3.3 (you can connect it to 5v if you need a stronger buzz and you can spare some battery life) 
- battery sensing via gpio 0
- vcc to 5v (from power switch and tp4056 out+)

### mounting orientation
when clipped upright to your collar:
- x-axis: parallel to the ground (lateral / left-to-right)
- y-axis: perpendicular to the ground (vertical / up-and-down)
- z-axis: normal to your chest (forward-and-backward)

## standalone mode
when away from your laptop (ble disconnected):
- the tag continues continuous 20Hz posture tracking using its calibrated baseline from NVS.
- after 2.5s of sustained forward slouching, the motor executes a double buzz (160ms on, 100ms off, 160ms on).
- if you dont correct your posture, it pulses a reminder buzz every 5 seconds.
- as soon as you straighten up, the vibration stops immediately.

## battery optimizations
i focussed on optimizing batterylife so it can last as long as possible:

- underclocked the esp32c3 from 160mhz to 80mhz which cuts active cpu current by aprox 50% while still having plenty of power for handling ble 5 and i2c.
- accelerometer only sensing (25 hz odr): the gyroscope is kept completely powered down (saving aprox 1mA). the accel runs in ultralow power mode.
- ble optimizations:
   - ble connection interval is 30ms - 60ms with slave latency of 4 intervals
   - 100-200ms advertising interval with scan responses disabled.
   - radio tx power set to 0 dbm (plenty for sitting in front of the laptop).
- freertos dynamic tick sleep: delay(50) lets the esp32 enter automatic light sleep between 20hz sensor reads.
- nonvolatile calibration: your upright posture baseline is stored in flash memory (Preferences.h), so it stays saved across power cycles.

## ble communication protocol
if you want to inspect the ble communication or make your own client, here is the protocol:

- **custom service uuid**: 19B10000-E8F2-537E-4F6C-D104768A1214
- **posture data characteristic (notify/read)**: 19B10001-E8F2-537E-4F6C-D104768A1214
- 12-byte packed binary struct (<hhhhBBBB):
    - int16_t pitch_x10: current pitch angle * 10
    - int16_t roll_x10: current roll angle * 10
    - int16_t baseline_x10: calibrated baseline upright pitch * 10
    - int16_t delta_x10: forward tilt delta * 10
    - uint8_t is_slouching: 1 if slouching, 0 if upright
    - uint8_t battery_pct: battery percentage (0-100)
    - uint8_t flags: bit 0 = calibrated, bit 1 = low battery (<=15%)
    - uint8_t seq: packet sequence counter
- **command characteristic (write)**: 19B10002-E8F2-537E-4F6C-D104768A1214
  - 0x01: calibrate current posture as baseline upright
  - 0x02 <threshold_deg_x10 (int16)>: update slouch threshold angle
  - 0x03 <mode>: update vibration mode (0=off, 1=standalone, 2=always)
  - 0x04: reset baseline calibration
- **standard ble battery service**:
  - service UUID: 0x180F
  - battery level characteristic: 0x2A19 (READ | NOTIFY, uint8 0-100%)

## building and flashing with platformio
i use platformio but you can use whatevertool that you prefer.