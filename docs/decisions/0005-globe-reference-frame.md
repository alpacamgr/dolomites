# 0005 - Globe geometry uses the PALEOMAP frame (Scotese and Wright 2018), superseding ADR 0003 for the globe

Date: 2026-09-06 - Status: accepted. Supersedes the "global backbone" clause of ADR 0003 for the globe view only.

## Context

The first plates build used Muller et al. 2019 (250-0 Ma, mantle reference frame) plus Matthews et al. 2016 (300-251 Ma). Overlaying its continent outlines on the PaleoDEM textures showed a mismatch of roughly ten degrees of latitude at 240 Ma and a visible rotation at 100 Ma: the PaleoDEM is built in the PALEOMAP reference frame, the Muller model in an optimised mantle frame. The model switch at 250 Ma also produced a 7 degree jump of the Dolomites marker. Measured Dolomites paleolatitude at 240 Ma: Muller 2019 1.4 N, Muller 2022 8.6 N, Merdith 2021 11.8 N, Scotese and Wright 2018 7.3 N; paleomagnetic measurements on Dolomites rocks give about 16-18 N (Muttoni et al. 1997, pending first-hand verification).

## Decision

Everything drawn on the globe (paleogeography raster, continent and coastline outlines, plate boundaries, the Dolomites marker and its paleolatitude readout) comes from one model: **Scotese and Wright 2018 / PALEOMAP** (rotations, static polygons, continental polygons, topologies; CC BY 4.0; obtained via gplately's PlateModelManager as `scotese_and_wright2018`), for the whole 300-0 Ma range. The raster and the vectors then share a reference frame by construction.

Muller et al. 2019 and Le Breton et al. 2021 stay cited in the narrative for the Alpine kinematics (Adria, Piemont-Liguria) and remain available in `data/raw/` for future regional views. ADR 0003 stands for those uses.

## Consequences

- The paleolatitude readout is labeled "PALEOMAP model" and the Triassic chapter states that paleomagnetic data from the Dolomites themselves place the region about ten degrees further north than the displayed model. Disagreement is content, per the data policy.
- No model switch, no jump; one attribution line for the globe.
- Plate boundaries come from PALEOMAP topologies. The model has no topologies older than 100 Ma, so the globe shows no plate boundaries before 100 Ma, and the legend says so. Boundaries from another model are not substituted, because they would sit in a different reference frame than the continents (decided 2026-09-12 after the rebuild).
- The model has no subduction polarity and no separate coastline layer, so the globe draws no subduction teeth.
- Continental polygons (and their union, `landmass`) mark continental crust, not shorelines; at 240 Ma they cut through the painted land of the PaleoDEM. The globe therefore draws no continent outlines by default. The coastline visible on the globe is the sea-level colour step of the PaleoDEM texture. Landmass and block outlines remain optional detail layers (decided 2026-09-12 after inspecting overlays at 240, 100 and 20 Ma).
- The Dolomites trail shows only the last 30 Myr of drift before the displayed age (presentation choice, 2026-09-12). The full 300 Myr path is in an absolute frame; drawn in full over a young globe it ran across Africa and suggested the region had been there. Untyped ("other") model boundaries are drawn faint for the same reason: they are model edges, not mapped faults.
- Measured after the rebuild: Dolomites paleolatitude 7.28 N at 240 Ma, 28.67 N at 100 Ma, -9.93 at 300 Ma. Plate files are 27-83 KB each.
