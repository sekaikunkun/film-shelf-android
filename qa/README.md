# Independent Android acceptance

Adapted from the [mobile-agent-testers method](https://github.com/pierridotite/mobile-agent-testers): give a tester a clean device, a role, explicit test flows and an evidence trail. This repo does not run Claude Code or send data to a model API. The development agent hands the exact APK and an already booted isolated emulator to a **different OpenAI agent** for acceptance. No API token or service setup is needed for the included ADB bridge. The existing GitHub build remains separate and does not run these UI checks.

## Handoff

Provide the branch SHA, APK SHA-256, lab ADB port, emulator serial and a synthetic provider. Never use household credentials, playback sources, or a personal device for this suite. Keep the APK, screenshots and logs local unless explicitly authorized to share them. Use Python 3.10 or later; installation uses the project's pinned Android build tools under `ANDROID_HOME`.

Example, replace the port, serial and digest with the actual isolated lab values:

```sh
python3 qa/android-device.py --port 15084 --serial emulator-5678 device
python3 qa/android-device.py --port 15084 --serial emulator-5678 install ./test.apk --sha256 "$APK_SHA256"
python3 qa/android-device.py --port 15084 --serial emulator-5678 start
python3 qa/android-device.py --port 15084 --serial emulator-5678 ui
python3 qa/android-device.py --port 15084 --serial emulator-5678 key DOWN
python3 qa/android-device.py --port 15084 --serial emulator-5678 screen ./evidence.png
```

## Tester brief: same-episode playback recovery

Test as a viewer using the remote. Do not change the app to make tests pass. Record each case as **pass**, **fail**, or **not tested**, giving the actual screen/behavior and evidence. A green build is not a UI pass. Keep logs or screenshots locally, and report a source as playable only with evidence of playback advancing.

1. Play episode 9. Enter the current-source scan with a working episode 9 on a reversed playlist. The working line must be offered and episode 9 must advance only after an explicit selection; scanning alone must not switch playback.
2. A manual-only line with a matching episode stays selectable. An HTTP-200 HTML response must not count as playable. Lines without an unambiguous episode 9 must not open episode 1.
3. Cancel or leave while the probe is slow. The results must not reopen, and playback must not switch.
4. With an explicit synthetic login response, verify the login message and wait beyond the normal timeout without a failover prompt; after login/retry, stay on the same episode. A message saying login is **not** required plus a network timeout is not an auth prompt.
5. Record build and installed APK hashes, guest ABI and actual page size. Record what was observed on this emulator separately from physical-device behavior and third-party provider compatibility.

Repeat this handoff before treating playback changes as feature-complete. A device or provider case not run is **not tested**, never silently passed.
