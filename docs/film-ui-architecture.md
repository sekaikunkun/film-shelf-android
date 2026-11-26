# Film Shelf UI architecture · staged migration

Status: architecture selected for review; no runtime or dependency change.
Baseline: local Film Shelf app `a3ca5a7`; QA-only branch tip `ffc5854`.
Goal: a calm, modern living-room and tablet UI, without changing the proven
catalog, playback and resume contracts. First approved runtime slice will be
home header plus its Search/Continue Watching handoff.

## Existing boundaries

- `leanback` and `mobile` are separate mode flavors, with separate ABI flavors;
  this plan starts in leanback ARM64 (including Y700). Current Gradle: AGP
  9.2.1, ViewBinding, Leanback 1.2.0 and Material Components 1.14.0;
  no Compose UI configured. SDK and ABI values are not migration targets.
- `HomeActivity` builds Leanback rows, loads `History.get()`, routes actions to
  `SearchActivity`, `SettingActivity` and `VideoActivity`, and hosts an optional
  `HomeWebController`. Keep routes, optional web mode, handlers and data
  ownership in place rather than moving them into Composables.
- `SearchActivity` routes into `CollectActivity`; Collect hands site/video
  identity into `VideoActivity`. Keep provider selection, aggregation and
  route arguments unchanged. Allow tablet and D-pad input paths to differ
  behind the same Search action.
- `VideoActivity` owns playback handoff, resume and line-scan dialog lifecycle.
  UI will ultimately reflect `FamilyPlaybackWait`, `FamilyScanProgress` and
  existing results. Exo/MPV, MediaSession, history DB, provider, authentication,
  matching and switch logic are explicitly not included.

## Evidence and decision

Reviewed November 26, 2026:
- [Android TV Compose guide](https://developer.android.com/training/tv/playback/compose)
  and [TV component releases](https://developer.android.com/jetpack/androidx/releases/tv):
  primary guidance for TV Material and component focus behavior. The release
  page lists TV Material 1.1.0 as stable; its availability does not verify the
  Film Shelf dependency graph. Do not combine mobile and TV Material themes in
  the same screen.
- [Compose in Views](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/compose-in-views):
  primary compatibility reference supports hosting a new UI section in existing
  Views, with state/lifecycle explicitly owned by the existing screen.
- [AGP built-in Kotlin](https://developer.android.com/build/migrate-to-built-in-kotlin):
  AGP 9 enables built-in Kotlin by default. Do not add the Kotlin Android plugin
  out of habit; resolve the compatible Compose compiler/BOM with the existing
  AGP toolchain in the first build. No version upgrade by implication.
- [Android TV navigation](https://developer.android.com/training/tv/get-started/navigation):
  remote directions, selection, and Back must have predictable outcomes. Test
  focus crossing the Compose/View boundary, not just rendering.
- [Google JetStream Compose sample](https://github.com/android/tv-samples/tree/main/JetStreamCompose)
  (sample README reviewed, not imported): useful for dark media surfaces and
  catalog composition, not a migration blueprint. Use current
  [scrollable-layout guidance](https://developer.android.com/training/tv/playback/compose/lists)
  instead of copying old TV lazy-container examples. For known upstream focus
  regressions and fixes use the release notes above; no upstream PR or player
  dependency is being integrated. No paper/benchmark can substitute for
  measuring this app's existing startup, focus and playback on its target.

| Option | Disposition |
| --- | --- |
| Keep Leanback Views and restyle layouts | Cheapest and safest short-term; leaves styles, navigation and callbacks coupled across screens. Keep as fallback. |
| Port the full Google sample / make the whole app single-Activity in one go | Not suitable: feature parity and focus rollback become hard; needlessly touches playback, history and source operations. |
| Shared visual language plus incremental Compose for TV in the existing screens | Recommended. Keeps stable activity/navigation and data ownership while letting individual UI sections migrate and roll back independently. |

## Architecture and design

- Shared design layer: dark neutral surfaces, warm text, one teal accent,
  common typography, spacing and shape tokens, and distinct normal/focused/
  pressed/selected/disabled states. Apple-like restraint in spacing, not a clone
  of tvOS or a requirement for expensive blur; Google TV focus conventions.
- Screen layer: small immutable display state for content, loading, empty and
  error; explicit user intents go back to the existing Java host. Keep selected
  item/restoration tied to a stable catalog identity, not row index. No fetches
  or playback decisions from Composables. Use a bridge at section/screen scale,
  not a Compose host per RecyclerView item.
- Input contract: touch activates on first valid tap; remote focus never
  submits; Center activates once; Back dismisses transient UI first and restores
  prior focus/scroll. Use text and icon as well as color for route statuses.
  Do not show fake progress or add animation that blocks interaction.
- Information order: search first, Continue Watching in first usable viewport,
  then browse; move lower-use utility actions to secondary navigation without
  deleting them. Keep live hidden. No new login or source onboarding.

## Stages and acceptance

1. **FS-UI-01, theme and Home entry.** TV Material theme, reusable focusable
   actions and accessible card patterns; embed the first header in native
   `HomeActivity` via one `ComposeView` behind a local fallback. Reorder
   existing rows to surface Continue Watching; reuse existing search, settings,
   history handlers and force no storage changes. The optional web mode retains
   its prior behavior. Record visual captures at Y700-like and TV aspect ratios.
2. **FS-UI-02, search and browse.** Reuse theme and action contract across
   search/results, with the system input path on touch and working D-pad
   keyboard navigation on TV. Preserve query, catalog filters and return focus.
   Then apply to settings and detail surfaces, not in the first patch.
3. **FS-UI-03, playback overlays.** Style login wait, retry and line scan with
   existing runtime state and true progress; retain reduced motion, cancellation,
   same-episode switching and no implicit supplier switch.

For FS-UI-01, run ARM64 build and 16 KiB package audit; compare old and new
APK size and cold launch on the same device, and report any regression before
promoting. Check touching Search once, remote focus/Center, Back restoring
focus, scrolling to Continue Watching, empty history, no duplicate requests,
and unchanged search → open → exit → resume with synthetic data. Test touch
emulator and D-pad; count Y700 or a TV as physically passed only when it was
actually observed. Rollback in dev: turn off the new native header/row branch
or revert its isolated patch; no data migration, new app ID or player change.
