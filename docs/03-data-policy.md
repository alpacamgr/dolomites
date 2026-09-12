# 03 - Data and honesty policy

This project exists because most popular visualizations of deep time blur the line between data and decoration. We draw the line explicitly.

## Four labels

Every visual element on the site carries exactly one of these labels, visible on hover or in the layer legend:

| Label | Meaning | Examples |
|---|---|---|
| **Observed** | Measured today. | LiDAR terrain, geological map units, glacier outlines, fault traces. |
| **Modeled** | Output of a published numerical model, cited with version. | Ice thickness from an ice-sheet model, plate positions from a rotation model, paleo-topography rasters. |
| **Interpreted** | Drawn by researchers from field evidence, published in a paper or map. | Triassic platform-and-basin sketch maps, stratigraphic columns, restored cross-sections. |
| **Illustrative** | Artwork or a schematic with no claim to spatial accuracy. | Reef life reconstructions, block diagrams, cartoon volcanoes. |

Two qualifiers may be added to a label where they help: **dated** (an observed or interpreted item whose age comes from a chronometer with a quoted uncertainty, e.g. cosmogenic exposure ages) and **compiled** (a harmonized multi-source database such as a glacier inventory or a proxy compilation). They refine a label; they never replace it.

If an element cannot be placed in one of these classes with a source, it does not ship.

## Rules

1. **Every dataset has a manifest** in `data/manifests/` before it is used: source URL, authors, version, license, download date, checksum, and the exact processing applied. See `data/manifests/TEMPLATE.yaml`.
2. **Every number in the narrative has a citation** in the timeline YAML or narrative front matter. Rounded numbers keep the precision of the source ("about 30 Ma", not "31.2 Ma" unless the source says so).
3. **Redrawn figures cite the original** by author, year, figure number, and license. We only redraw figures whose license permits derivative works (CC BY, CC BY-SA, public domain) or where we have written permission. Redrawings live in `assets/figures-redrawn/` with a sidecar `.md` file.
4. **Model outputs keep the caveats of the model.** When we show ice from an ice-sheet model, the legend says which model, which run, and what resolution. When we show plate positions, the legend names the rotation model.
5. **Disagreement is content, not noise.** Where sources disagree materially (for example on the cause of Ladinian magmatism or the timing of uplift), the narrative presents the alternatives.
6. **No interpolation that creates false detail.** Upsampling a 1-degree paleogeography raster to look like 30 m terrain is fabrication. Coarse data is shown coarse, or is used only for context views at the scale it supports.
7. **Research notes carry verification tags.** In `research/`, each cited fact is tagged `[verified YYYY-MM-DD]` (source opened and checked), `[from search, not opened]`, or `[unverified - from memory]`. Unverified claims never reach `content/`.
8. **Licenses are respected in full**, including attribution text and share-alike obligations. The license register in `research/sources/` lists every dataset with its license and required attribution string.

## Review

Before a chapter is published, a reviewer with geological training reads it against its sources. Their sign-off is recorded in the front matter of the chapter.
