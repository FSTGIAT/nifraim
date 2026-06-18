# Headless Android emulator for testing the Nifraim SMS forwarder.
# Runs accelerated via /dev/kvm (passed in at `docker run --device /dev/kvm`).
# Used because the host user is not in the `kvm` group and sudo is interactive —
# the Docker daemon (root) mediates KVM access for the container.
FROM eclipse-temurin:17-jdk-jammy

ENV ANDROID_SDK_ROOT=/opt/android-sdk
ENV PATH=$PATH:/opt/android-sdk/cmdline-tools/latest/bin:/opt/android-sdk/platform-tools:/opt/android-sdk/emulator

# Emulator (swiftshader software GL) + adb runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        unzip wget ca-certificates \
        libpulse0 libnss3 libxcomposite1 libxcursor1 libxi6 libxtst6 \
        libasound2 libgl1 libglx-mesa0 libx11-6 libxext6 libxfixes3 \
    && rm -rf /var/lib/apt/lists/*

# Android command-line tools
RUN mkdir -p /opt/android-sdk/cmdline-tools && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O /tmp/cmdline.zip && \
    unzip -q /tmp/cmdline.zip -d /opt/android-sdk/cmdline-tools && \
    mv /opt/android-sdk/cmdline-tools/cmdline-tools /opt/android-sdk/cmdline-tools/latest && \
    rm /tmp/cmdline.zip

# SDK packages + system image (google_apis required for SMS console support)
RUN yes | sdkmanager --licenses >/dev/null 2>&1 || true
RUN sdkmanager --install \
        "platform-tools" \
        "emulator" \
        "platforms;android-30" \
        "system-images;android-30;google_apis;x86_64" >/dev/null

# Create the AVD
RUN echo "no" | avdmanager create avd -n nifraim -k "system-images;android-30;google_apis;x86_64" -d pixel

COPY boot.sh /boot.sh
RUN chmod +x /boot.sh
CMD ["/boot.sh"]
