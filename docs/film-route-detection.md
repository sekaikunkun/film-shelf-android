# Playback route detection

Selecting **Check other routes** does not change the playing source. The probe
can now ask HTTP type-4 providers to resolve one candidate episode at a time.
It uses an independent, cancellable request and never calls the foreground
player's source resolver. Unsupported interactive parsers, scripts, DRM and
credential-bearing media headers remain manual.

A playable result requires a decoded first frame plus forward playback progress.
Explicit authorization responses stay distinct from a timeout, HTML response
or other unverified result. Same-source probes match episode labels, including
simple Chinese ordinals; missing or ambiguous matches are not tried. An
unverified provider remains a manual option, not an automatic redirect.

## Verification

- ARM64 debug build and 16 KiB package check, with no optional TMDB token.
- 23 playback and route-policy unit tests.
- Exact-APK touch replay on an ARM64 Android 15 emulator with a 16 KiB page
  size, using only a loopback synthetic type-4 catalog and generated video.
- Physical tablet/third-party provider compatibility is outside this run.
