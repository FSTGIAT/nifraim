#!/bin/bash
# Build the Nifraim SMS APK inside the emulator image (has JDK17 + Android SDK).
# Bootstraps the gradle wrapper jar (absent from the repo; CI regenerates it too).
set -e

echo "=== installing SDK 34 packages ==="
yes | sdkmanager 'platforms;android-34' 'build-tools;34.0.0' >/dev/null 2>&1

echo "=== fetching gradle 8.7 ==="
cd /tmp
wget -q https://services.gradle.org/distributions/gradle-8.7-bin.zip
unzip -q gradle-8.7-bin.zip
export PATH=/tmp/gradle-8.7/bin:$PATH

cd /work
echo "=== bootstrapping wrapper jar ==="
gradle wrapper --gradle-version 8.7 --distribution-type bin >/dev/null 2>&1

echo "=== assembleRelease ==="
gradle assembleRelease --no-daemon

echo "=== APK output ==="
ls -lh /work/app/build/outputs/apk/release/
