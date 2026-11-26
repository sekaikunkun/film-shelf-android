# Film Shelf Home touch scroll

2026-11-26 Beijing; base f199466. Y700 with the configured source: three 650 ms upward swipes all left the same first five titles and y coordinates after waiting, despite visible list motion during longer swipes. Scope: native modern Home vertical list, not provider/web mode, card data, playback or other screens.

The exact installed Leanback grid 1.0.0 bytecode in `GridLayoutManager.onLayoutChildren` enters `focusToViewInLayout` with realignment true when not smooth-scrolling and its strategy is ALIGNED, independent of touch mode. In the otherwise existing window relayout, it can realign the old selected row. [AndroidX BaseGridView](https://developer.android.com/reference/androidx/leanback/widget/BaseGridView) describes the focus strategies; the shipped bytecode, not the newer published API, determines this app's behavior. Use ITEM (no such realignment) only while touching native Home, return to original aligned behavior when Android leaves touch mode. Retain current framework scroll gestures, nested horizontal rows and focus restoration; do not synthesize panning or change dependencies. Rollback is the scoped patch.

Recovery anchor: build ARM64, try repeated short and long up/down swipes at the same Y700 scale and after settle, then select through D-pad. Keep existing source and application data.

## Verified
Exact build SHA-256 `fef13d2104da5266dbfc4d793598a10e016433a191749ad29aae0e5e4048ae40`. ARM64 build, touch/D-pad layout checks, 16 KiB audit and 21 playback-policy tests passed. Installed in place on the Y700 with the unchanged user source. First and second identical 650 ms swipes each left a different row set that stayed in place after settling; a third ended at the same lower position, not back at the first row. The opposite-direction swipe moved back and also stayed put. One-tap Search still opened; D-pad Down focused Home content without activating it. Existing APK retained locally for rollback. No public push.
