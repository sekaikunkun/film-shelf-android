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

## Reproduce with a local fixture

The synthetic CMS exposes normal, reversed, ambiguous, slow, manual and fake-video responses, plus a one-time QR challenge and a negated timeout. Generate a short test MP4 with movement and no real content, then run:

```sh
ffmpeg -f lavfi -i testsrc2=size=640x360:rate=24 -t 90 -c:v libx264 -pix_fmt yuv420p -movflags +faststart qa-motion.mp4
python3 qa/synthetic-provider.py qa-motion.mp4 --port 18656
```

Configure only the **disposable emulator** to reach the loopback fixture through its dedicated ADB server and explicitly selected serial. For an existing dedicated session, use `adb -H 127.0.0.1 -P <lab-port> -s <lab-serial> reverse tcp:18656 tcp:18656`. In Film Shelf, enter `http://127.0.0.1:18656/config.json` as the VOD source. Restart the fixture to reset the one-time QR response. Remove only this reverse mapping when done. Do not grant broad storage access for a network-only acceptance test.

For cross-source playback, repeat using the fixture's `/cross.json` catalog. Start the first supplier's Episode09, choose Change → Find other sources with Auto Change enabled, wait for search results without selecting anything, then click Scan. No foreground request or provider change may occur before explicit selection. Verify that the scan results retain the original episode name and offer EP01. The second supplier puts a playable trailer before EP01. Only `/cross01.mp4` may be probed or played. Wait for playback to advance after selecting the result; verify `/trailer.mp4` was never requested.

For detail-identity regression, use `/cross-identity.json`. Search from the original Episode09, then scan the four synthetic suppliers. `Identity ordered` returns the wrong ID first with the same title; it must still find the requested item. `Identity wrong-only` and `Identity duplicate` must remain unconfirmed and neither may trigger a media request. `Identity changes` is valid during scanning, then returns a different ID with the *same* episode label and URL when selected. Click it first: it must show “未切换” and keep the original Episode09 playing. Then reopen the scan and select `Identity ordered`; EP01 must advance. Check the fixture log: no request to `/wrong-title.mp4` or `/trailer.mp4`, and the rejected choice must not make a new playback request. Restart the fixture to reset the changing-detail counter.

For startup permission regression, leave all-files access off and cold-launch twice. Wait at least three seconds each time to cover the old delayed prompt, distinguish the separate Android notification prompt, then play the network fixture. Verify that entering one explicit local-file flow still provides its permission entry if needed; do not grant access.
