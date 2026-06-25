#!/bin/bash
# Boot the AVD inside Xvfb (windowed) and expose it via noVNC so a browser can
# view + interact at http://localhost:6080/vnc.html
set -e

export DISPLAY=:0
Xvfb :0 -screen 0 1400x2200x24 >/dev/null 2>&1 &
sleep 2

adb start-server
emulator -avd nifraim \
    -no-audio -no-boot-anim -no-snapshot \
    -gpu swiftshader_indirect -accel on \
    -netdelay none -netspeed full >/dev/null 2>&1 &

adb wait-for-device
echo "Device detected, waiting for boot_completed..."
until [ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; do
    sleep 2
done
adb shell input keyevent 82 || true
echo "=== EMULATOR BOOT COMPLETE ==="

# VNC server on the Xvfb display, then a websocket+web bridge for the browser.
x11vnc -display :0 -forever -nopw -shared -rfbport 5900 >/dev/null 2>&1 &
websockify --web=/usr/share/novnc 6080 localhost:5900 >/dev/null 2>&1 &
echo "=== VNC READY: http://localhost:6080/vnc.html ==="

tail -f /dev/null
