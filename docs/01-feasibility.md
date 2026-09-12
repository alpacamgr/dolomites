# 01 - Feasibility assessment

Date: 2026-09-06. Based on the six research notes under `research/`. Every dataset named here is catalogued there with its license and verification tag.

## Verdict

**Feasible, with one honest constraint.** A scroll-driven site that replays the geological history of the Dolomites can be built entirely from open, citable data. The constraint is scale: plate motion and paleogeography exist as data only at continental to regional scale (hundreds of km), while the Dolomites are about 100 km across. The site must therefore switch between two views: a coarse globe or regional view for the plate chapters, and a high-resolution terrain view for the chapters where local data exists (present-day rock, ice ages, uplift). What does not exist anywhere, and will not be invented here, is a local elevation model of the Dolomites at any past age.

This is not a weakness to hide. No serious visualization of deep time can do better, and the ones that appear to (painted paleo-terrain) are illustration. Our difference is that we say so on screen.

## What can be shown, chapter by chapter

| Chapter | Age | What is on screen | Data | Label |
|---|---|---|---|---|
| Where the Dolomites were | 300 Ma to today | Globe: continents, plate boundaries, a marker following the future Dolomites, paleolatitude readout | Muller et al. 2019 rotation model (+ Matthews 2016 for 300-250 Ma); Le Breton et al. 2021 for Adria and the Alpine Tethys; both CC BY 4.0 | modeled |
| Tethys land and sea | 300 Ma to today | Coarse paleogeography (land, shelf, deep ocean) at 5 Myr steps, regional extent only | Scotese and Wright 2018 PaleoDEM, 0.1 deg, CC BY 4.0 | interpreted |
| Permian volcanoes | 284-274 Ma | Present-day outcrop of the Athesian Volcanic Group on terrain; localities | CARG / PAB geology (CC0 for South Tyrol), TINITALY 10 m (CC BY 4.0) | observed |
| Werfen sea, Permian-Triassic boundary | 252 Ma | Outcrop; the Tesero and Bulla sections as markers | CARG / PAB geology; GSSP and reference sections from literature | observed |
| Triassic reefs and basins | 247-230 Ma | (1) Outcrop of Sciliar, Cassian, Marmolada platforms on terrain, colored by unit; (2) a redrawn platform-and-basin sketch map; (3) a restored cross-section; (4) numbers: platform height ~800 m, basin depth hundreds of m, paleolatitude ~16-18 N | (1) geology maps; (2)(3) Bosellini, Gianolla and Stefani 2003, CC BY-NC, figure numbers still to confirm; (4) Muttoni et al. 1997 and IUGS Latemar page, to be verified first-hand | observed / interpreted |
| Ladinian volcanoes | ~238 Ma | Predazzo and Monzoni intrusions and Wengen volcaniclastics on terrain; duration under 0.7 Myr | geology maps; Storck et al. ages (to verify) | observed |
| Burial: Dolomia Principale to Scaglia | 228-66 Ma | Outcrop of each unit; a stratigraphic column growing with time; sea-level and temperature curves on the rail | geology maps; PhanDA (CC BY 4.0); Haq curves only with caveat | observed / modeled |
| Collision and uplift | 40-9 Ma to today | Fault traces (Valsugana, Giudicarie, Periadriatic); exhumation timing 17-9 Ma; present uplift 1-1.5 mm/yr as a labeled number | geology maps; Zattin et al. 2006 (to verify); Sanchez et al. 2018 GNSS grid, CC BY 4.0 | observed / modeled |
| Ice ages | 120 ka to today | Animated ice thickness over real terrain at 1 kyr steps; LGM extent outline; deglaciation dates; Holocene rock avalanches | Seguinot et al. 2018 PISM output, 1 km, CC BY 4.0; GLACIMONTIS 2026 LGM extent; Rossato 2025, Ivy-Ochs 2013/2017 (to verify) | modeled / interpreted / dated |
| Today | 0 | Full-resolution terrain, glacier outlines since the Little Ice Age, geosites | TINITALY 10 m, Bolzano DTM 2.5 m (CC0), RGI 7.0, Reinthaler and Paul 2025 (CC BY 4.0) | observed |

The Triassic chapter, the emotional center of the site, is the one where "simulation" is least available and "showing the real rock" is most powerful. The platforms are still there, at their original geometry, lightly deformed and unmetamorphosed. Coloring the modern terrain by rock unit literally draws the Triassic reefs and basins on the mountains. That is the honest version of a paleo-map, and it is stronger than a painting.

## What cannot be shown, and what we do instead

| Wish | Why not | Instead |
|---|---|---|
| Elevation map of the Dolomites at 240 Ma, 100 Ma, 20 Ma | No dataset exists at that scale. PaleoDEM cells are 10-110 km. | Regional PaleoDEM labeled interpreted, plus restored cross-sections and platform-height numbers from literature. |
| The Dolomites moving as their own block | No published model resolves anything smaller than Adria (Le Breton 2021 splits Adria in two, nothing finer). | Show Adria moving, with the Dolomites as a fixed marker on it, and say so. |
| A physical plate-tectonic simulation | Kinematic models are fits to data, not simulations; running our own would be fabrication. | Replay the published model and name it. |
| Exact width of the Tethys ocean | Published models disagree by hundreds of km; Piemont-Liguria maximum ~250 km in Le Breton 2021. | Show one model and state the range from Jolivet 2023. |
| The year the Dolomites became land | No source states one; Miocene, with cooling 17-9 Ma. | State the range and the evidence. |
| Smooth motion between 5 Myr paleogeography frames | Interpolating rasters invents intermediate coastlines. | Crossfade between frames and label the crossfade as presentation. |

## Data readiness

| Need | Status | Blocking issue |
|---|---|---|
| Plate model, global | Ready. CC BY 4.0, pygplates-readable. | None. |
| Plate model, Alpine | Ready. Le Breton 2021 files hosted by EarthByte. | Plate IDs for the two Adria pieces to read from the .rot file. |
| Paleogeography raster | Ready. Zenodo, CC BY 4.0. | Must be presented at native resolution only. |
| Present-day terrain | Ready. TINITALY 10 m CC BY 4.0; Bolzano 2.5 m CC0; Copernicus GLO-30 free. | Trentino LiDAR license to confirm per dataset; Veneto is IODL 2.0. |
| Geological map | Partly ready. South Tyrol vector geology CC0; CARG 1:50k as WMS. | CARG vector redistribution license unclear; may have to stay WMS-only. |
| Faults | Ready. DISS 3.3.1 CC BY 4.0. | ITHACA license unclear. |
| Ice-sheet model | Ready. Seguinot 2018, ~1 GB NetCDF, CC BY 4.0. | Pick one forcing variant and document why. |
| LGM extent | Ready. GLACIMONTIS 2026 open geodatabase. | Ehlers and Gibbard shapefiles have restrictive terms; do not use. |
| Glaciers today and LIA | Ready. RGI 7.0; Reinthaler and Paul 2025 CC BY 4.0. | None. |
| Climate and sea level curves | Ready. PhanDA CSV, CENOGRID, Spratt and Lisiecki. | Haq curves are contested; use with caveat or omit. |
| Uplift today | Ready. Sanchez et al. 2018 grid, CC BY 4.0. | None. |
| Paleolatitude | Ready via paleolatitude.org 3.0 CSV export or computed from the rotation model. | No API; export once and store. |
| Triassic sketch maps | Candidate. Bosellini et al. 2003 is CC BY-NC. | Figure numbers unconfirmed; NC forbids commercial use of the site. Fondazione Dolomiti UNESCO material returned 403, license unknown. |
| Time axis | Ready. ICS chart 2026/06. | Stage boundary ages must be copied from the chart itself, not from notes. |
| UNESCO system polygons | Not found as download. | Ask the Foundation or digitize from the nomination map. |
| Chronology numbers in the narrative | Draft. Most literature ages were captured from search summaries. | Every Ma value needs a first-hand check against the primary PDF before publication. This is the largest remaining research task. |

## Risks

1. **License creep.** The CARG vector data and the Bosellini figures are the two items most likely to force a design change. Mitigation: WMS-only for CARG, and a non-commercial site or our own sketch drawn from the geological map rather than from the figure.
2. **False precision from secondhand numbers.** About three quarters of the literature citations in the geology note were read from search summaries. Mitigation: the verification pass in the next steps, and the rule that unverified claims never reach `content/`.
3. **Scale confusion for the visitor.** Switching from a 10 km-cell globe to 10 m terrain can suggest the globe was as precise. Mitigation: the view switch is an explicit, narrated moment, and the globe never zooms past its cell size.
4. **Terrain hosting size.** Terrain tiles for the region at zoom 14 will be hundreds of MB. Mitigation: PMTiles on object storage; verify host limits before building the pipeline.
5. **Ladinian and Latemar debates.** Presenting them well takes editorial care. Mitigation: they are content, per the data policy.

## Recommended first prototype

Two chapters, end to end, to prove the pipeline and the honesty UI:

1. **Ice ages** on real terrain: TINITALY terrain tiles + Seguinot ice frames + RGI outlines + LGM extent. Everything is open and clearly labeled; it is visually dramatic and technically representative (rasters over terrain, time scrubbing).
2. **Where the Dolomites were**: globe with Muller 2019 + Le Breton 2021 continents and a marker, 300-0 Ma at 1 Myr, with a paleolatitude readout.

If both work, add the Triassic chapter, which needs the geology vector tiles and the verified numbers.

## Next steps

1. Verification pass on the geology note: open the primary PDFs for every "not opened" citation that carries a number; record results in `research/sources/bibliography.md`. Opus agents, one per paper cluster.
2. Read the Bosellini et al. 2003 open-access PDF; record figure numbers and decide on redraw versus own sketch.
3. Write the ICS 2026/06 stage table into `content/ics-chart.json` from the chart itself.
4. Download and manifest the prototype datasets (TINITALY tiles for the bbox, Seguinot continuous NetCDF, Muller 2019 bundle, Le Breton 2021 files, RGI 7.0 region 11, GLACIMONTIS).
5. One-day spike: MapLibre globe versus d3-geo for the plate view; MapLibre terrain with a PMTiles archive for the terrain view. Then write ADR 0004 (rendering stack).
6. Ask Fondazione Dolomiti UNESCO for the nine system polygons and for figure reuse terms.
