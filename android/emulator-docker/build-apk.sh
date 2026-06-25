#!/bin/bash
# Build the Nifraim app inside the emulator image (has JDK17 + Android SDK).
# Produces BOTH a release APK (for the in-app QR sideload path) and a release
# AAB (for the Google Play closed-testing upload).
# Bootstraps the gradle wrapper jar (absent from the repo; CI regenerates it too).
set -e

echo "=== installing SDK 35 packages ==="
yes | sdkmanager 'platforms;android-35' 'build-tools;35.0.0' >/dev/null 2>&1

echo "=== fetching gradle 8.7 ==="
cd /tmp
wget -q https://services.gradle.org/distributions/gradle-8.7-bin.zip
unzip -q gradle-8.7-bin.zip
export PATH=/tmp/gradle-8.7/bin:$PATH

cd /work
echo "=== bootstrapping wrapper jar ==="
gradle wrapper --gradle-version 8.7 --distribution-type bin >/dev/null 2>&1

echo "=== assembleRelease + bundleRelease ==="
gradle assembleRelease bundleRelease --no-daemon

echo "=== APK output ==="
ls -lh /work/app/build/outputs/apk/release/
echo "=== AAB output ==="
ls -lh /work/app/build/outputs/bundle/release/
