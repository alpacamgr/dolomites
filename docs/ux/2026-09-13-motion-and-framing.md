# Motion and framing polish (2026-09-13)

Status: in progress. Worktree `worktree-agent-a82c4ca6db051b10a` off `main`.
Scope from the coordinator: gestures, chapter transitions, camera flights,
globe framing and slice crossfade. The parallel terrain-look agent owns the
geology paint, palette, ice and DEM pipeline; this pass does not touch those.

Owner feedback under attack: "the map does weird shifts, blurrs, earth plate
movements etc" and "it doesn't really feel professional/fun/interesting enough".

## Decisions

1. **Wheel over the stage does nothing but scroll the page.** Both the terrain
   (MapLibre `cooperativeGestures`) and the globe (`.gl-hint`) painted a dark
   full-stage veil on every plain wheel tick; on a 62 %-of-viewport stage that
   flashed constantly while the reader scrolled. Fix:
   - Terrain: `cooperativeGestures` off, `scrollZoom` disabled at build time
     and kept out of `applyLock`, custom `wheel` listener only preventsDefault
     and eases the zoom when `ctrlKey`/`metaKey` is held. `touch-action:
     pan-x pan-y` on the container gives back the one-finger-scrolls / two-
     fingers-move behaviour that cooperative gestures used to enforce.
   - Globe: the `.gl-hint` full-stage veil is removed. Its `showHint` prop is
     kept as an optional no-op so `GlobeControls` does not need touching by
     the terrain agent's parallel work; wheel handling in `controls.ts` was
     already correct (Ctrl/⌘ to zoom, plain wheel falls through to the page).
   - No replacement chip: we deliberately dropped the hint rather than
     showing anything conditional. "Ctrl + scroll to zoom the map" is well
     enough discovered by trial and MapLibre's own popup on the geology
     units already teaches map interaction; adding a chip would be
     speculative UI.

2. **View switch is a hard cross to background, not an overlap.** The
   engine manager used to fade both layers simultaneously for 650 ms with
   both engines painting; the outgoing globe would ghost over the incoming
   coloured geology. Replaced with a two-phase sequence: fade the outgoing
   engine to the stage background over 260 ms, then fade the incoming
   engine in over 380 ms. The incoming terrain camera jumps to the chapter
   position while its layer is still opacity 0 (see 3.), so nothing lurches
   during the fade-in. `prefers-reduced-motion` still swaps instantly. The
   value lives in `FADE_OUT_MS` / `FADE_IN_MS` in `engineManager.ts` and is
   applied inline, so CSS and JS cannot drift; the docs table in
   `2026-09-timeline-and-geology-ux.md` was updated to match.

3. **Terrain camera flights are longer and gentler.** `CAMERA_MS` raised
   from 1100 to 1800 ms with the existing ease-in-out. `CAMERA_AFTER_
   SWITCH_MS` (formerly 900 ms of ease-out during the crossfade) is now 0:
   the camera jumps while the incoming layer is still hidden by the fade. (Review fix, same
   day: the reveal now also waits for the incoming engine to be mounted with its camera set,
   so this holds on slow mounts too, and a flip-back mid-fade no longer cuts to black.)
   Chapter yamls: `06-collision-uplift.yaml` pitch tightened from 30 to
   45 and zoom raised from 8.4 to 8.9 so the DEM bounds fill the frame and
   the hard right-hand edge of the data rectangle is out of view. Bearings
   across `05` `07` `08` still vary by design (each chapter cares about a
   different part of the massif); `06` now shares bearing 20 with `05` and
   `07` so the collision flight from either side is straight-in, not a
   swoop. Sky/fog values in `buildStyle` untouched (they already dissolve
   the far edge into the horizon at pitch ≤ 60).

4. **Globe framing and slice crossfade.**
   - Framing: added `fitDistance()` to the globe engine so a chapter's
     `distance` is lifted to whatever value makes the sphere fit inside
     ~72 % of the stage height (rail plus legend take the rest). Yaml
     chapter cameras still declare their per-chapter framing; the engine
     just guarantees a floor. Marker stays inside the visible disc.
   - Slice mix: `globeFragmentShader` now dissolves the two 5 Myr slices
     with `smoothstep(0.78, 1.0, mixAmount)` instead of a linear mix. Each
     native step is held for ~78 % of its interval and dissolves into the
     next in the last ~22 %. This matches the honest reading of PaleoDEM
     at its 5 Myr steps: discrete slices with brief dissolves, not a
     permanent double image.
   - Landmass outline: the four globe chapters (`01`–`04`) add `landmass`
     to their `style` so the PALEOMAP continental-crust outline draws
     faintly over the blurry paleogeography texture, giving the coast
     something to read against. `STYLE.landmass.opacity` lowered from 0.5
     to 0.28 so the outline is a hint, not a line drawing. It is model
     data; the chapter still labels the layer `modeled` and cites the
     same reference (Scotese & Wright 2018).

5. **Chapter time easing.** `TAU_CHAPTER` (rail catch-up after a chapter
   change) raised from 200 to 350 ms. The Ma readout no longer races
   through 300 Myr in one blink on the intro → Permian jump; the number
   feels connected to the map. `TAU_SCROLL` (in-chapter damping) unchanged.

## Files touched

- `app/src/lib/terrain/index.ts` (gestures, camera timing)
- `app/src/lib/story/engineManager.ts` (sequenced fade)
- `app/src/lib/story/controller.ts` (TAU_CHAPTER)
- `app/src/lib/globe/index.ts` (fitDistance, hint removed)
- `app/src/lib/globe/controls.ts` (hint no-op)
- `app/src/lib/globe/shaders.ts` (smoothstep mix)
- `app/src/lib/globe/overlays.ts` (STYLE.landmass opacity)
- `app/src/styles/global.css` (`.gl-hint` removed)
- `content/timeline/01-world-permian.yaml` … `08-today.yaml` (cameras / style)
- `docs/ux/2026-09-timeline-and-geology-ux.md` (motion table)

## Measurements

- **Type check.** `npx astro check`: 0 errors, 0 warnings, 0 hints.
- **Console errors during a full 9-chapter QA sweep in en / de / it.** 0 errors, 0
  exceptions, 0 log-entry errors from Chrome DevTools. Only browser cache
  `net::ERR_CACHE_READ_FAILURE` entries appear (fresh headless profile, cold cache);
  those are not application errors.
- **Terrain wheel policy end-to-end test in a real Chromium** (Browser pane):
  - Plain wheel on the terrain stage: `preventDefault` false, no
    `.maplibregl-cooperative-gesture-screen` element created, page still scrolls.
  - Ctrl+wheel on the terrain stage: `preventDefault` true; zoom eases in 120 ms.
  - `touch-action` on the terrain slot: `pan-x pan-y` (single-finger scrolls the
    page, two fingers reach MapLibre).
  - `.gl-hint` element is gone from the DOM (globe hint fully removed).
- **View-switch fade.** The mid-transition capture at t=300 ms into a
  terrain→globe fade (previously showed the globe ghosting over the coloured
  geology, see `qa-live-trans/01-world-permian-p2-t250.png`) now shows the
  incoming globe fading in from black with no trace of the previous scene
  (see `qa-v2-trans/01-world-permian-p2-t300.png`).
- **Terrain camera flights.** Same-view flight raised from 1100 ms to 1800 ms
  with ease-in-out; view-switch flight is a jump (was 900 ms ease-out during
  the crossfade). Verified via `qa-v2-trans` mid-transition captures.
- **Globe framing.** `fitDistance` = `1 / (0.72 · tan(FOV/2))` = 3.35 with
  FOV 45°. Chapter distances 2.3–2.7 are lifted to 3.35, and the sphere now
  sits inside the visible stage with air around it (see
  `qa-v2/01-world-permian-p50.png`), instead of being cut top and bottom
  under the rail (see `qa-live/01-world-permian-p10.png`). Marker stays
  visible on the disc.
- **Slice dissolve.** Smoothstep dissolve in `[0.78, 1.0]` of each 5 Myr
  interval; a slice is held for ~78 % of its span. Captured at mid-slice
  (e.g. Permian at 274.4 Ma, well inside the [275, 280] step) the coast
  reads as one image, not a double exposure. Rendering cost unchanged
  (one extra `smoothstep` per fragment).
- **Landmass outline.** Faint (opacity 0.28, width 1.0) PALEOMAP continental
  outline draws on every globe chapter (`style: continents+boundaries+landmass`).
  Cited as `modeled`, same reference as the plate model (Scotese & Wright 2018).
- **Rail catch-up on a chapter change.** `TAU_CHAPTER` 200 → 350 ms. The
  intro → Permian transition's readout no longer flashes through 300 Myr in
  a single frame; the rail marker travels visibly with the fade.

Files sizes: initial JS bundle unchanged in shape; MapLibre no longer bundles
its cooperative-gesture DOM/CSS path at runtime (behavior only).

## Anything decided against

- **Fabricated coastlines / inter-slice warping.** The finding explicitly
  forbids fabricated data, and the smoothstep dissolve is the honest
  reading of a step function. No morph between slices, no invented
  intermediate geometry.
- **A "Ctrl+scroll to zoom" chip.** Considered; dropped as speculative UI.
  Owner will surface it in a follow-up if the plain "wheel does nothing"
  behaviour reads as broken during their preview.
- **Rewriting per-chapter globe distances in every yaml.** The engine
  floor (`fitDistance`) is enough and adapts to viewport height; leaving
  the yaml values gives the chapter its intended relative framing.

## Open questions for the owner

- Do you want the small "Ctrl + scroll to zoom" microcopy in the credits
  panel, or is the current silent behaviour acceptable?
- The globe landmass outline is faint but present on chapters 01–04. If
  it distracts from the PaleoDEM texture, we can drop the `+landmass`
  token and revert `STYLE.landmass` opacity in one commit.
- Collision-uplift chapter was framed wide (zoom 8.4, pitch 30). New
  framing (zoom 8.9, pitch 45) still shows the whole thrust belt but
  crops the DEM's south edge. Confirm this is the trade-off you want.
