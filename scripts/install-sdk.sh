#!/usr/bin/env bash
set -euo pipefail
sdk="${1:?Android SDK destination required}"
archive="$(mktemp)"
trap 'rm -f -- "$archive"' EXIT
curl --fail --silent --show-error --location --retry 3 \
  https://dl.google.com/android/repository/commandlinetools-linux-16111833_latest.zip -o "$archive"
printf '%s  %s\n' '0877a1d048fe4a24efe2eff536ca4223f7adeb58648bb81909d33c446918cfa8' "$archive" | sha256sum -c
mkdir -p "$sdk/cmdline-tools"
unzip -q "$archive" -d "$sdk/cmdline-tools"
mv "$sdk/cmdline-tools/cmdline-tools" "$sdk/cmdline-tools/latest"
manager="$sdk/cmdline-tools/latest/bin/sdkmanager"
(set +o pipefail; yes | "$manager" --sdk_root="$sdk" --licenses >/dev/null)
"$manager" --sdk_root="$sdk" "platforms;android-37.0" "build-tools;37.0.0" "ndk;29.0.14206865" "cmake;3.22.1"
[[ -f "$sdk/platforms/android-37.0/android.jar" ]]
[[ -x "$sdk/build-tools/37.0.0/zipalign" ]]
