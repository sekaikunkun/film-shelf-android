#!/usr/bin/env bash
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
sdk=${ANDROID_SDK_ROOT:-/work/sdk}
platform=${HOME_PROBE_PLATFORM:-$sdk/platforms/android-37.0/android.jar}
tools=${HOME_PROBE_TOOLS:-$sdk/build-tools/36.0.0}
output=${1:?Usage: build.sh /path/to/home-probe.apk}
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
mkdir -p "$scratch/classes"
javac --release 8 -classpath "$platform" -d "$scratch/classes" "$source_dir/HomeProbe.java"
"$tools/d8" --min-api 26 --lib "$platform" --output "$scratch" "$scratch/classes/io/github/sekaikunkun/filmshelf/homeprobe/HomeProbe.class"
"$tools/aapt2" link -I "$platform" --manifest "$source_dir/AndroidManifest.xml" -o "$scratch/packed.apk"
jar uf "$scratch/packed.apk" -C "$scratch" classes.dex
"$tools/zipalign" -f 4 "$scratch/packed.apk" "$scratch/aligned.apk"
keytool -genkeypair -keystore "$scratch/qa.jks" -storepass android -keypass android \
    -alias homeprobe -dname 'CN=Disposable Film Shelf QA' -keyalg RSA -keysize 2048 -validity 7
"$tools/apksigner" sign --ks "$scratch/qa.jks" --ks-pass pass:android \
    --out "$scratch/signed.apk" "$scratch/aligned.apk"
"$tools/apksigner" verify "$scratch/signed.apk"
cp "$scratch/signed.apk" "$output"
