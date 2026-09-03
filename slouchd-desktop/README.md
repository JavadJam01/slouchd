# slouchd-desktop

this is the desktop client (or deamon) for slouchd. it sits quietly in your system tray and monitors your posture in the background to dim your screen(s) and alert you when you slouch.

as mentioned in the main readme, slouchd-desktop supports two perception sources:
- **wearable collar tag (ble)**: connects over ble to the slouchd-tag clipped to your collar for 100% camera-free, offline and privacy-friendly posture monitoring.
- **webcam (computer vision)**: uses a lightweight google mediapipe pose model estimation to track your shoulders and nose when you don't have the hardware tag or prefer using your camera.

## features

- **multi-monitor screen dimming**: when you slouch, it dims all your connected displays with a smooth transparent clickthrough overlay (without messing with your actual monitor hardware settings)
- **super light on resources**: designed to stay running 24/7 in the background without eating your cpu or ram (uses <1% cpu on windows and <0.5% on linux).
- **system tray deamon**: runs quietly in your tray with status indicators (active, slouching, paused, and tag battery readout).
- **customizable sensitivity & grace period**: you can adjust grace period (1s to 10s) and slouch angle threshold so you don't get annoyed by false alarms during natural movement.
- **sound alerts**: optional sound warnings if screen dimming alone isn't enough to catch your attention.

## calibration

first thing you need to do is to calibrate your baseline posture:

- **with wearable tag**:
  1. turn on your slouchd-tag and clip it to the front of your collor.
  2. open the app, right click the tray icon and click on **calibrate** (or open it from settings).
  3. sit upright
  4. click **calibrate baseline**. the app saves your baseline locally and also syncs it with the tag. (you can also see check it via the ui guage)

- **with webcam**:
  1. select webcam in settings or the tray context menu.
  2. open "calibrate posture" sit facing the camera upright, and click **calibrate baseline**.
