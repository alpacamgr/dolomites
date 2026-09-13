# 2026-09-13 - Terrain look and data extent

Polish pass on the terrain view before the site is shared with friends. See owner feedback in the tasking prompt.
Worktree: `.claude/worktrees/agent-aee75e6347a79e211`; branch: `worktree-agent-aee75e6347a79e211`.

## Measurements before any change (baseline)

`scratchpad/qa-live/` holds 1440x900 headless screenshots for every chapter at 10%/50%/90% progress.

Per-source area share of the visible viewport at each terrain chapter (see
`scratchpad/check_view.py`, z11 tiles clipped to a lon/lat bbox that fits the
camera at pitch 30-64, 1440x900 canvas, tile geometry only):

| view       | bbox                        | total (Mm2) | coarse-source share      | Quaternary/Holocene yellow |
|-----------:|:----------------------------|------------:|-------------------------:|---------------------------:|
| intro      | 10.95-12.50, 46.00-46.60    |      16 945 |  Veneto 37.9%, ISPRA 10.0% = **47.9%** | **31.5%** |
| reefs      | 11.00-12.30, 46.15-46.55    |       9 470 |  Veneto 32.3%, ISPRA 9.3% = **41.6%**  | **31.5%** |
| collision  | 10.40-12.50, 45.85-47.10    |      47 714 |  Veneto 20.1%, ISPRA 20.9%, GeoSphere 15.1% = **56.1%** | **28.7%** |
| today      | 11.70-12.00, 46.35-46.55    |       1 094 |  Veneto 42.6%, ISPRA 0.1% = **42.7%**  | **30.6%** |
| full bounds| 10.30-12.70, 45.80-47.20    |      61 189 |  ISPRA 22.5%, GeoSphere 22.1%, Veneto 19.0% = **63.6%** | **27.4%** |

So half of most views is coarse-source drape, and about a third is Quaternary/Holocene yellow. That is
what "some sections are completely different that the rest, some are just yellow" refers to.

Whole-bounds check with 6000 sampled points (`data/scripts/terrain/check_geology_tiles.py`,
`scratchpad/geology-check.json`) confirms the split. Coarse-source undated share at z13: ISPRA 37.2%,
GeoSphere 13.5%, others below 6.3%.

DEM/geology bounds (baseline): both stop at 10.3-12.7 E, 45.8-47.2 N
(`app/public/data/terrain/elevation/tiles.json`, `.../geology/tiles.json`). Pitched cameras look past
that edge (top-right of `qa-live/05-triassic-reefs-p10.png`) and the near-top-down collision camera
shows the DEM as a rectangle against the page background (bottom-right of
`qa-live/06-collision-uplift-p50.png`).

Ice at 102 ka is nearly invisible outside the deep valleys against the near-white summit tint
(`qa-live/07-ice-ages-p10.png`); at 56 ka essentially none is legible over the mountains
(`qa-live/07-ice-ages-p50.png`), although `app/public/data/terrain/ice/56.webp` has thin ice over most
high ground.

## Decisions

1. **Geology drape** (finding 1). Cut base fill opacity 0.7 -> 0.55, raise soft hillshade exaggeration
   0.34 -> 0.50 so relief carries more of the picture. Coarser-source polygons get an extra 0.75
   factor on the fill (unchanged hue keeps legend identity, mirrors printed atlases that lighten less
   detailed compilations). Undated wash 0.5 -> 0.34.
2. **Reef emphasis** (finding 2). Focus fill 0.88 -> 0.72 and dimmed 0.10 -> 0.30 so context still
   reads under the highlight; `geology-line` opacity/width bumped when the same feature matches the
   focus, so emphasised units get a crisp edge without a flat magenta block.
3. **Coarse-source treatment** (finding 3). The lighter wash on coarse sources (see 1); the legend key
   already carries the "coarser maps in view" string, extended with a short "shown a bit lighter than
   the detailed maps" explanation, and translated to de/it.
4. **Ice legibility** (finding 4). `ICE_DISPLAY_STOPS` cooled and lifted at low thickness (0-80 m),
   so thin ice reads as pale blue rather than white-on-white. Model values are unchanged; only the
   display ramp is edited (per docs/04 2.3 and `ice.ts` comment).
5. **Map edge** (finding 5). Option (b): tune sky/fog so the DEM edge dissolves into the horizon,
   widen `maxBounds` and lower `minZoom` so a whole-region zoom-out no longer hits background. Draw
   the DEM bbox as a soft "extent of the maps" line under geology when geology is on, and the geology
   coverage outline when the gaps layer is off. Legend explains it. Option (a) (a coarse GLO-30 outer
   ring) was scoped and deferred: it would take a build_terrain_pmtiles rerun with a wider bbox plus
   an export at z6-z9 outside the core; safe in principle (MapLibre falls back to parent tiles when
   z10-12 are missing), but too large for this pass. Recommended follow-up in the report.
6. **Hypsometric tint** (finding 6). No change; the ice-ramp cooling already restores the summit-vs-ice
   distinction. Verified against `qa-after`.

## Verification

After changes: `qa-after/` (same script, same ports, same chapters). Screenshots compared with
`qa-live/` per chapter. Frame time at the reefs camera captured through
`tools/qa/screenshot-chapters.mjs`'s built-in `console.time` (reported at end of run).

## Follow-up recommendations (not applied in this pass)

- Coarse outer-ring DEM (option a) at z6-z9 for bbox 9.0-14.0 E, 45.0-48.0 N. Source: existing raw
  GLO-30 (10-13 E, 45-48 N) plus new GLO-90 tiles for the 9-10 E and 13-14 E strips (from the public
  AWS bucket `copernicus-dem-90m`). Total added bytes budget under 25 MB. Requires a
  `build_terrain_pmtiles.py` mode that emits only z6-z9 outside the core bbox, and a widened
  `tiles.json` bounds; ice frames stay on their own bounds. See finding 5 above.
- Chapter camera cushion (owned by the motion agent, recommended here): move `05-triassic-reefs`'s
  pitch from 64 to about 55 or shift the target latitude up by 0.02 deg so the top edge of the frame
  stays over rock, not sky, at 1440x900.
