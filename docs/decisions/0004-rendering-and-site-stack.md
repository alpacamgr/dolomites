# 0004 - Rendering and site stack

Date: 2026-09-06 - Status: accepted

## Context

The site needs two visual modes: a whole-Earth globe that plays 300 Myr of plate motion and paleogeography with smooth crossfades, and a high-resolution 2.5D terrain view of the Dolomites with time-varying overlays (ice, geology, glaciers). It must look professional at retina resolution, stay at 60 fps on a mid-range laptop, and be hosted statically in three languages. Versions below were checked against the npm and PyPI registries on 2026-09-06.

## Decision

| Concern | Choice | Version checked | Why |
|---|---|---|---|
| Globe view | three.js | 0.185.1 | Full shader control for two-texture crossfade, lighting, atmosphere; the paleogeography is a sphere texture per time slice, which is exactly what three.js does best. MapLibre globe can draw a globe but cannot crossfade whole-sphere textures cleanly. |
| Terrain view | MapLibre GL JS | 6.7.0 | Best open 2.5D terrain engine: GPU hillshade, raster-dem terrain, vector overlays, smooth camera, BSD license, no vendor account. CesiumJS is heavier and pushes toward Cesium ion terms; a custom three.js terrain would mean writing tile streaming ourselves. |
| Tiles | PMTiles | JS 4.5.0, Python writer | One file per tileset, served by HTTP range requests from any static host; no tile server. |
| Site framework | Astro + Svelte 5 islands, TypeScript | Astro 7.3.1 | Static output, built-in i18n routing for de/it/en, islands keep the heavy engines out of the initial bundle. |
| Pipeline | Python 3.13 venv: pygplates 1.0.0, gplately, xarray, netCDF4, pyproj, shapely, Pillow, numpy, pmtiles; rasterio if a wheel installs | | pygplates has a 3.13 Windows wheel; everything else is pure-Python or has wheels. |

## Rules that follow

- Textures for the globe are 4096 x 2048 (2048 x 1024 on small screens), which is the native 0.1 degree resolution of the PaleoDEM. The globe never zooms closer than the point where one texture pixel exceeds two screen pixels, so it never looks pixelated.
- The terrain view uses 10 m data (TINITALY) where available and never exposes zoom levels beyond what the data supports.
- Engines load lazily when their chapter is within one viewport of the scroll position.
- Device pixel ratio is capped at 2; render loops run only while the time or camera is changing.

## Consequences

Two rendering engines in one page. They never run simultaneously; the inactive one pauses its loop and releases GPU textures it does not need. The content schema and data contracts (`docs/04-data-contracts.md`) are engine-agnostic so either engine can be swapped later.
