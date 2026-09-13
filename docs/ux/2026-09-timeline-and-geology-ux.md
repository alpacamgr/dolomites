# Timeline, motion and geology key: UX plan (2026-09)

Status: design plan written before implementation, 2026-09-12. Trigger: owner feedback that the rock-age map "is a bit broken" where data is missing, and that the timeline and its animation should be smoother and easier to understand.

## Problems (from the 1440x900 production screenshots)

A. Time rail. A 4 px, 300 Ma linear bar with unlabelled period colours. On terrain chapters the big readout says "today" while a small "Topic: Middle Triassic" says the chapter is about 247-237 Ma. In the ice-age chapter (120 ka to 0) the marker cannot move visibly on a 300 Ma scale. The chapter nav is nine anonymous dots. Time jumps between chapters.

B. Motion. Scroll maps linearly to time and is applied next frame, so wheel scrolling moves time in visible steps; chapter changes snap the time; the view crossfade (400 ms) and the terrain camera ease (800 ms) are not coordinated.

C. Geology map. No colour key. Undated units and areas without an open map are transparent and read as broken. `fill-antialias` off gives jagged edges. Pale Quaternary ICS colours at 0.55 opacity look like missing data. The dashed coverage outline is unexplained. Popup strings are English only.

Data checks behind the decisions below (z10 tiles, 2026-09-12):
- 62 distinct unit colours; the largest class is Holocene `#FEEBD2` (about 38 % of features).
- `#9AD9DD` is both Phanerozoic (eon) and Aalenian (age) in the ICS chart, so a colour alone does not identify an interval; the unit's younger bound `age_min_ma` disambiguates (the colour is the colour of the younger named interval, whose `end_ma` is `age_min_ma`).
- Some units are named only at era level (e.g. "Paleozoico", 251.9-538.8 Ma), some are older than the chart window (Ordovician to Devonian, colours not in `ics-chart.json`).
- Overlap with the Middle Triassic (247-237 Ma): 12.5 k features lie fully inside it; about 9 k more overlap only through very wide envelopes (e.g. 473 Myr ranges like "Paleozoico (?) - Mesozoico (?)"). Highlighting every overlapping unit would paint Paleozoic basement as "Middle Triassic". See decision G3.

## Design decisions

### 1. Hierarchy: which time, which map

The rail head always answers two questions in this order:

1. **Chapter time** (large, tabular numerals). Globe and ice chapters: the scrolled time, animated. Chapters that show today's terrain but discuss the past (`subject_age_*`): the subject interval, e.g. "247 – 237 Ma". The word "today" is only the large readout when the chapter really is about today.
2. **Interval name** (small caps, with ICS swatch): the period · epoch at the current time, or the subject interval's epoch(s). No "Topic:" prefix any more; the hierarchy carries it.
3. **What the map shows** (one muted line with a view glyph): "Reconstruction at this time" (globe) or "Today's terrain" plus what is draped on it: "rocks coloured by mapped age", "modelled ice at this time", "glaciers today". Built from the chapter's view and layer ids; no geology in code. Paleolatitude stays on this line for globe chapters.

### 2. Timeline

- **Broken axis with a magnified inset.** Left part: 300 Ma to the inset start, linear. Right part: the last ~130 ka, linear, separated by a break mark and its own scale label. The inset span is derived from the chapters (largest ka chapter start plus 8 %); without ka chapters there is no inset.
- **Lens transition.** In Ma chapters the inset takes 16 % of the axis width; in ka chapters it grows to 62 %. The split animates (see motion spec), so the marker visibly travels 120 ka to 0 in the ice-age chapter.
- **Two ICS rows.** A 14 px period band with names inside (localized via `ics_names`; full name if it fits, else a truncated name with a full stop if at least three letters fit, else no text but a tooltip and aria text) and a 4 px epoch strip below it. The inset shows the epochs/ages that fall inside its span. Names and colours only from `ics-chart.json` and `content/ui/*.json`.
- **Chapters on the axis.** A lane under the band draws each chapter's interval (subject interval if present, else its scene time range) as a thin bracket, with a numbered button at its centre. Buttons that would overlap are relaxed apart (minimum 18 px spacing, reading order kept). The active chapter's bracket is solid white; hovering or focusing a button shows its title in a tooltip and outlines its bracket. Buttons keep `aria-current="step"`, `aria-label="n. title"` and full keyboard access. The anonymous dot nav is removed.
- **In-chapter progress.** A 2 px reading-progress bar along the bottom edge of the rail panel, plus "n / 9" in the head.
- **Mobile (< 900 px).** Full-width rail, one line head (time and interval), map line truncated with an ellipsis, band without the chapter lane and without scale ticks except the ends. Legend starts collapsed.

### 3. Motion spec

| What | Behaviour |
|---|---|
| Displayed time inside a chapter | Exponential damping toward the scroll target, frame-rate independent: `x += (target - x) * (1 - exp(-dt / tau))`, tau = 90 ms (settles in ~0.4 s). One rAF loop in the controller; runs only while not settled (threshold 0.02 % of the chapter span or 0.01 unit), then stops. |
| Across a chapter change | The rail number and marker continue from the previous value (converted to Ma) and ease to the new target with tau = 350 ms (raised from 200 in 2026-09-13 so the readout does not race through 300 Myr in a blink; see `2026-09-13-motion-and-framing.md`). Engines receive the new chapter's target time directly in `setState` (no replay of meaningless intermediate states in the new view). |
| Engine `setTime` | At most once per frame, only when the eased value changed by more than the threshold; never while settled. |
| Axis lens (inset width) | Eased with the same damping loop, tau = 160 ms (~0.7 s). |
| Subject readout / interval name swap | 180 ms opacity crossfade. |
| View crossfade (globe <-> terrain) | Two-phase sequence (2026-09-13): 260 ms fade of the outgoing engine to the stage background, then 380 ms fade of the incoming engine in. Both engines are never visible at once, so the two scenes cannot overlay. `FADE_OUT_MS` / `FADE_IN_MS` live in one place (`engineManager.ts`) and are applied inline, so CSS and JS cannot drift. |
| Terrain camera | Same view: 1800 ms ease-in-out (2026-09-13, raised from 1100). On a view switch the incoming terrain camera jumps to the chapter position while the incoming layer is still hidden by the fade; the first time the terrain is shown it jumps too (no flight from the default camera). |
| Digits | `font-variant-numeric: tabular-nums` on all readouts. |
| `prefers-reduced-motion` | No damping (time follows scroll), no lens animation, no crossfade (instant swap), camera jumps. |

### 4. Geology key

Shown inside the legend panel whenever a geology layer is active.

- **Present intervals only.** The terrain engine reports the unit colours and age bounds rendered in the current view (`queryRenderedFeatures` on `idle`, deferred to an idle callback and only after the camera or tiles changed), plus whether undated units, gap areas and Veneto 1:250k units are in view. A client module groups them with the ICS chart: colour + `age_min_ma` identifies the younger named interval; that interval's period is the row. Rows are youngest first (map-legend convention). Each row shows the localized period name and a strip of the actual colours present in that period (finer shades = finer ICS divisions). Units named only at era or eon level form their own row ("Paleozoic, period not given"); units older than the chart window form a row "Older than the Permian" whose bound comes from the chart.
- **Explicit non-data swatches.** "Mapped, age not given" (the same light neutral fill the map uses) and "No open geological map here" (the same hatch the map uses; only when `geology-gaps.geojson` is present, otherwise a line swatch "Limit of open geological maps" for the coverage outline).
- **Veneto note.** "Coarse 1:250,000 map in view (Veneto)" when such units are rendered.
- **Hover / focus highlights.** Hovering or focusing a row calls `TerrainEngine.setGeologyFocus({ colors })` (or `{ undated: true }`); other units are dimmed. Components never touch MapLibre.
- **Chapter emphasis (G3).** New optional scene field `scene.emphasis: { age_start_ma, age_end_ma }`. The terrain engine emphasises units whose **mapped age range lies within** the interval and dims the rest; the key shows a first row "Rocks mapped as Middle Triassic (247–237 Ma)" (interval name from the chart). We deliberately do not use plain overlap: at z10 it would also emphasise about 9 k features with envelopes of hundreds of millions of years.

### 5. Gaps and undated units

- `geology-gaps.geojson` (named by `coverage.gaps_file` in the meta; optional): diagonal hatch (fill-pattern generated on a canvas at runtime) over a faint veil, with a hover popup "No open geological map covers this area. This is a gap in open data, not an absence of rock."
- Undated units: light neutral fill (warm white, distinct from every ICS colour in use) at reduced opacity, matching their key swatch.
- `fill-antialias` on if the measured frame cost is negligible.
- Geology fill opacity raised from 0.55 to about 0.7 so pale Quaternary colours stay visible; hillshade stays on top.
- Popup strings localized (en/de/it), including the new `age_basis` property when present (from the map's own age / from the map legend / from a rule for the rock class).

## Files touched

`app/src/components/TimeRail.svelte`, `ChapterNav.svelte` (removed; merged into the rail), `Stage.svelte`, `Legend.svelte`, new `GeologyKey.svelte`, `app/src/lib/story/controller.ts`, `engineManager.ts`, `types.ts`, new `app/src/lib/story/timeAxis.ts` and `geologyKey.ts`, `app/src/lib/terrain/index.ts`, `palette.ts`, `app/src/lib/scene-api.ts`, `app/src/lib/content/schema.ts`, `app/src/pages/[lang]/index.astro`, `app/src/styles/global.css`, `content/ui/{en,de,it}.json`, `content/timeline/05-triassic-reefs.yaml`, `docs/04-data-contracts.md`.

## Outcome (implemented 2026-09-12)

Implemented as planned, with these changes found during QA:

- **Key query cost.** A whole-view `queryRenderedFeatures` on the reefs camera returned 41 k features in 73-100 ms. The engine now queries a 6x4 grid of boxes across idle callbacks (at most ~10 ms per callback) and abandons the pass if the camera moves.
- **Antialiasing.** `fill-antialias` on vs off while orbiting the reefs camera (vsync off): 927/949 fps vs 836/929 fps, i.e. no measurable cost; it stays on.
- **Band labels** abbreviate to four letters (Perm., Tria., Cret.) instead of the longest prefix that fits, which produced forms like "Cretaceou.".
- **Subject readout** applies only when the scene time is static; the ice-age chapter has a subject interval but animates time, so it shows the moving age.
- **GeologyKey** is loaded lazily when the terrain engine first reports geology, to keep it out of the initial bundle.
- **Era names** Paleozoic, Mesozoic, Phanerozoic added to `ics_names` in de/it, checked against the text of the ICS 2022/02 German and Italian chart PDFs named in `ics_names_sources`.
- **Gaps** are only drawn when the meta names `coverage.gaps_file`; tested by serving the meta with that field through CDP interception, since the file had landed but the meta did not name it yet.

Performance (headless Chrome, RTX 5090, vsync off, production build; scroll = 240 frames of continuous scroll through the chapter; task = main-thread task time per frame from CDP metrics; idle = task time per second with no input):

| Chapter | fps before | fps after | task ms/frame before | after | idle ms/s before | after |
|---|---|---|---|---|---|---|
| world-permian (globe) | 374 | 794 | 1.15 | 1.00 | 0.04 | 0.05 |
| triassic-reefs (terrain, geology) | 579 | 521 | 0.18 | 0.26 | 0.04 | 0.05 |
| ice-ages (terrain, ice frames) | 180 | 206 | 5.37 | 4.68 | 0.05 | 0.04 |

fps in headless mode is bimodal and noisy; the task times are the more reliable comparison. Initial JS (Stage + Svelte client + renderer): 55.5 KB raw / about 22 KB gzip before, 66.9 KB raw / 26.4 KB gzip after; the growth is the time rail.

## Polish round (2026-09-12, coordinator review)

1. **Legend footprint.** While the rock-age key is shown, the layer list collapses to one line: honesty badge plus short layer name per layer, with the full name, citation and label explanation on the badge tooltip and aria-label. Period rows sit in a two-column grid; long rows ("…, period not given", "Pre-…", "Mapped, age not given", "No open geological map here") span the full width; when several era- or eon-only rows are in view they merge into one row, "Period not given: Cenozoic, Mesozoic, Paleozoic", whose hover highlights all of them. The footnote is two short sentences. The desktop legend has no scroll container (only windows shorter than 760 px get one); mobile keeps the legend collapsed and single-column. The QA tool now logs the legend's share of the stage, internal scrolling and overlap with the rail for every capture.
2. **Broken axis.** Ticks in the magnified part always carry their unit ("100 ka", "50 ka"); round Ma values stay bare next to the "300 Ma" start label. Labels are placed by measured width, ends first, so nothing collides at 390 px. The break is a double slash across the period band and epoch strip (gap widened from 1.6 % to 2.6 %), and chapter brackets that cross it are split in two, so the gap runs through the chapter rows as well. The chapter tooltip opens below the scale labels so it never hides them.
3. **Chapter badges.** One row per map type, marked with the view glyph: reconstructions (globe) above, today's terrain below. Within a row a chapter is placed only if it belongs to the longest run whose axis order matches reading order; so the rows read 2 3 4 5 and 6 7 8 9. That rule removes the intro, which shows today before the story begins and would otherwise sit at "today" between 8 and 9. Reading order stays explicit through a "‹ n / 9 ›" stepper in the rail head (also on mobile, where the rows are hidden); its buttons are labelled with the previous or next chapter's title. The next chapter's badge gets a brighter ring, the current one is filled; badges keep their title tooltip on hover and focus and an accessible name "n. title (interval)".
4. **More geology sources.** The "coarser map in view" note lists every source in view whose `meta.sources[].scale` denominator exceeds 25,000, named by localized source name and scale, one or several. Source display names come from `geology_popup.source.<dataset_id>` in content/ui (en/de/it) for all six known ids, with the English map in the engine only as a fallback and the meta title after that. The gaps hatch is drawn as soon as the meta names `coverage.gaps_file` (checked earlier by serving the meta with that field).

Verified against the data agent's update of 2026-09-12 (six sources, `coverage.gaps_file` present): with no front-end edits, the reefs view lists "Geological Map of Italy (ISPRA) 1:100,000; Veneto lithology map 1:250,000; Geological units of Austria (GeoSphere Austria) 1:500,000" as coarser maps (swisstopo GeoCover at 1:25,000 is correctly not listed), the gaps swatch replaces the coverage-edge swatch, and a "Cenozoic, period not given" row appears where units are named only at era level. The first band label after the axis break is padded so the break slashes never cover it.

Later in the same round: thin gap parts (`mean_width_m` below 200 m, mostly seams along map-sheet borders) are not hatched, outlined or given a popup; files without that property hatch every part. When a gaps layer is loaded the per-source coverage outline is hidden, since the key then shows the gap swatch instead of the edge swatch. The `age_basis` value `none` adds no popup line (the popup already says no age is given). The geology layer credits all six maps through a `source_ref` list.
