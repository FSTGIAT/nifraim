#!/bin/bash
# Build the Nifraim app inside the emulator image (has JDK17 + Android SDK).
# Produces BOTH a release APK (for the in-app QR sideload path) and a release
# AAB (for the Google Play closed-testing upload).
# Bootstraps the gradle wrapper jar (absent from the repo; CI regenerates it too).
set -e

echo "=== upgrading cmdline-tools ==="
# The Dockerfile pins cmdline-tools 11076708 (r11), which predates API 36.
# Upgrading sdkmanager first and then using the NEW binary is the sequence proven
# to work (locally, 2026-07-27); whether r11 alone can fetch android-36 was never
# tested, so don't rely on it.
yes | sdkmanager "cmdline-tools;latest"
export PATH="$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$PATH"
yes | sdkmanager --licenses >/dev/null 2>&1 || true

echo "=== installing SDK 36 packages ==="
# API 36 is required by Play from 2026-08-31. compileSdk 36 needs AGP >= 8.10,
# which in turn needs Gradle >= 8.11.1 — keep all three in step.
# Deliberately NOT silenced: this used to be `>/dev/null 2>&1`, so a failure here
# aborted under `set -e` with no clue why.
yes | sdkmanager 'platforms;android-36' 'build-tools;36.0.0'

echo "=== fetching gradle 8.11.1 ==="
cd /tmp
wget -q https://services.gradle.org/distributions/gradle-8.11.1-bin.zip
unzip -q gradle-8.11.1-bin.zip
export PATH=/tmp/gradle-8.11.1/bin:$PATH

cd /work
echo "=== bootstrapping wrapper jar ==="
gradle wrapper --gradle-version 8.11.1 --distribution-type bin >/dev/null 2>&1

echo "=== assembleRelease + bundleRelease ==="
gradle assembleRelease bundleRelease --no-daemon

echo "=== APK output ==="
ls -lh /work/app/build/outputs/apk/release/
echo "=== AAB output ==="
ls -lh /work/app/build/outputs/bundle/release/
