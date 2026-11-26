# Film Shelf Home probe

A standalone Android instrumentation APK for the Home entry point. It does not
modify Film Shelf, enter a tap, save a hierarchy, or return source names,
URLs, titles, or arbitrary screen text. It polls the active accessibility root
directly rather than waiting for the entire screen to become idle.

Build inside the Film Shelf build environment with JDK, Android SDK platform,
and existing build tools. The signing key is disposable and separate from the
app; build outputs are not tracked.

```sh
bash qa/home-probe/build.sh /work/home-probe/home-probe.apk
```

Run only on the explicitly selected, authorized QA device. Before installing,
check that the probe package is not already installed; do not replace it. Open
Film Shelf Home and keep that screen active until the probe returns.

```sh
adb -s "$serial" install /path/to/home-probe.apk
adb -s "$serial" shell am instrument -w \
  io.github.sekaikunkun.filmshelf.homeprobe/.HomeProbe
adb -s "$serial" uninstall io.github.sekaikunkun.filmshelf.homeprobe
```

On success, the result contains only `home_controls_found` and click-point
coordinates for Search and Settings. No coordinates are returned for another
foreground app or missing or ambiguous Home controls. Check foreground again
immediately before using a returned coordinate in separate test automation.
A non-success result is not a product failure or authorization to use guesses.
The probe does not establish cause for any older hierarchy timeout.

Verified with aarch64 Android 15 emulator (16 KiB pages) and Film Shelf
`a3ca5a7`: another foreground package returned no coordinates; three
successive Home runs found both buttons; one tap at the Search point opened
SearchActivity. The stock dump also worked on this emulator, so that run does
not reproduce the Y700 timeout. The separate probe was removed after QA. The
physical Y700 run is still pending.
