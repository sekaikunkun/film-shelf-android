# Film Shelf native UI update

The native TV/leanback interface shares a restrained palette across Home, catalog tabs, search cards and episode controls. The headline artwork experiment remains optional and is disabled by default. Empty Continue Watching no longer takes up Home space. The artwork fallback and episode UI do not change playback engines, source configuration or history storage.

This patch applies to the pinned public upstream used by `scripts/prepare.sh`. It contains only the application code and resources for the public build. The optional TMDB integration requires explicit configuration and defaults to no token. Treat any value supplied at build time as part of the resulting APK; never include a private token in a distributable package.

## Verification scope

The publication check builds the patched public base without private configuration. ARM64 build, the existing playback-policy tests, static touch/D-pad contracts and the 16 KiB APK audit are separate from device UI acceptance. No APK, device logs, account data, source lists, private repositories or Git submodules are bundled in this branch update.

Verified local ARM64 debug APK SHA-256: `ea5e6e2eb5a262172b6343b193b840244722a2da27359df931f00824c57e91eb`. The public build used an empty TMDB token.
