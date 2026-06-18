#!/bin/bash
# Boot the AVD headless with KVM acceleration and keep the container alive.
set -e

# Start adb server
adb start-server

# Launch emulator headless. swiftshader_indirect = software GL (no host GPU needed).
emulator -avd nifraim \
    -no-window -no-audio -no-boot-anim -no-snapshot \
    -gpu swiftshader_indirect -accel on \
    -netdelay none -netspeed full &

# Wait for device, then full boot
adb wait-for-device
echo "Device detected, waiting for boot_completed..."
until [ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; do
    sleep 2
done
adb shell input keyevent 82 || true   # dismiss lock screen
echo "=== EMULATOR BOOT COMPLETE ==="

# Keep container running
tail -f /dev/null
