# 00 - Vision and scope

## The idea

A single long page. You scroll, and time moves. At the top you are about 280 million years ago in a volcanic landscape near the equator. As you scroll, the land sinks under a warm sea, reefs grow into towers, volcanoes erupt between them, the sea deepens, the whole region is buried, then squeezed and lifted as the African promontory Adria pushes into Europe. Rivers and glaciers cut the valleys, and you arrive at the present-day Dolomites in full-resolution terrain.

Beside the story runs a time axis with the geological periods, a paleolatitude readout, and, where real data exist, a sea-level or temperature curve.

## Geographic focus

**Primary:** the Dolomites, roughly the UNESCO World Heritage area and its surroundings (10.5-12.5 E, 46.0-47.0 N), covering South Tyrol, Trentino, and Belluno.

**Context:** the whole Alps and the western Tethys / Mediterranean region for the plate-tectonic chapters, because plate motion is only meaningful at that scale.

Reasoning: the Dolomites are the best-documented mountain group in the Alps for the Triassic story (the reason they are a World Heritage site), have exceptional open elevation data from the province of Bolzano, and the Alpine story can be told through them. Widening the primary focus to South Tyrol or the whole Alps would multiply data work without adding a stronger narrative. Recorded in [decisions/0002-scope-dolomites-first.md](decisions/0002-scope-dolomites-first.md).

## What the site must do

1. Scroll-driven timeline from the Permian (about 300 Ma) to today, with chapter stops at each major stage.
2. A map or 3D terrain that changes with time, using only data we can cite.
3. Clear visual labeling of what is measured, what is modeled, what is interpreted from field evidence, and what is illustration.
4. Present-day terrain at high resolution with geological units and key localities.
5. A citation for every fact, reachable from the interface.
6. German, Italian, and English.

## What the site will not do

- It will not fabricate paleo-elevation maps of the Dolomites. No dataset of local elevation through time exists; any "Triassic terrain" is an interpretation and must be shown as such (see the feasibility doc).
- It will not run a physical simulation of plate tectonics. It replays published kinematic reconstructions.
- It will not claim precision the sources do not have. Where the literature disagrees, the site says so.
- It is not a hiking or tourism app.

## Audience

Curious adults and older students who visit or live in the region. Geologists should find nothing wrong; non-geologists should find nothing boring.

## Success criteria for the first release

- A geologist from the region reviews the chapters and finds no factual errors.
- Every visual layer has a working source link.
- The page loads and scrolls smoothly on a mid-range laptop and a recent phone.
