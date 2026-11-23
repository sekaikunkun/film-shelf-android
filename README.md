# Film Shelf for Android TV

An independent, GPLv3 Android TV playback experiment based on [WebHomeTV](https://github.com/webhtv/webhtv/tree/d187f6ae8bfaf0a4720724281d0a91186c57f73d) and FongMi/TV. It does not ship a media catalog, provider credentials, or installation keys. Add an authorized media source manually in the app.

The TV variant puts Search first, hides Live, distinguishes an explicit login prompt from a playback failure, and can check supported direct alternate sources without interrupting playback. It only offers a switch after rendering and advancing video; sources needing unsupported parsers or credentials still require manual testing. From Change, a plain catalog can also test alternate lines for the current episode without switching suppliers or guessing an episode by playlist position.

This repository contains the source changes and reproducible build recipe, not upstream binary copies. The build fetches a pinned public upstream snapshot and checksum-verified Python dependencies. See the upstream license and third-party notices/locks in that snapshot. CI builds and tests an independent ARM64 debug APK; there is no public binary release pending a third-party redistribution review. Binary alignment checks are not Android runtime tests.

## Build

Install JDK 21, Python 3.10, Android SDK 37.0, Build Tools 37.0.0, NDK 29.0.14206865 and CMake 3.22.1. Set `ANDROID_HOME`.
Run `bash scripts/prepare.sh "$PWD/build/upstream"` and then `bash scripts/check.sh "$PWD/build/upstream"`.

Source changes: GPL-3.0, as provided in LICENSE. Upstream components keep their applicable licenses.
