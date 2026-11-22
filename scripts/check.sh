#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "${1:?prepared source directory required}"
bash gradlew --no-daemon --max-workers=3 \
  :app:testLeanbackArm64_v8aDebugUnitTest \
  --tests 'com.fongmi.android.tv.ui.activity.FamilyPlaybackWaitPolicyTest' \
  --tests 'com.fongmi.android.tv.ui.activity.FamilyRouteProbePolicyTest' \
  :app:assembleLeanbackArm64_v8aDebug
mapfile -t apks < <(find app/build/outputs/apk/leanbackArm64_v8a/debug -type f -name '*.apk')
[[ ${#apks[@]} == 1 ]]
"${ANDROID_HOME:?}/build-tools/37.0.0/zipalign" -c -P 16 4 "${apks[0]}"
python3 "$root/scripts/audit-apk.py" "${apks[0]}"
sha256sum "${apks[0]}"
