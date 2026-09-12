# 0003 - Plate reconstruction backbone: Muller et al. 2019 + Le Breton et al. 2021

Date: 2026-09-06 - Status: accepted for Alpine kinematics in the narrative; superseded for the globe view by [0005](0005-globe-reference-frame.md)

## Context

The plate-tectonic chapters need one consistent kinematic model to animate. Candidates are catalogued in `research/tectonics/plate-reconstruction-data.md`. Requirements: covers 300-0 Ma, open license, machine-readable, treats Adria as a distinct plate, consumable by pygplates.

## Decision

- Global backbone: **Muller et al. 2019** deforming-plate model (250-0 Ma, CC BY 4.0, Zenodo 10.5281/zenodo.10525286), extended for 300-250 Ma with Matthews et al. 2016 or Muller et al. 2022 from the same EarthByte lineage.
- Regional overlay for Adria and the Alpine Tethys: **Le Breton et al. 2021** (Solid Earth, CC BY 4.0), which is built on the same rotation lineage and splits Adria into a northern and southern part.
- Paleogeographic background: **Scotese and Wright 2018 PaleoDEM** at 0.1 degree and 5 Myr steps (CC BY 4.0), labeled *interpreted* and never displayed below its cell size.

## Consequences

- The site can state paleolatitude, Adria's motion relative to Europe and Africa, and the opening and closing of the Piemont-Liguria ocean with a citation.
- The site cannot and will not show the Dolomites as a block moving independently of Adria; no published model does.
- Where the Adria-as-promontory and Adria-as-microplate camps disagree, the narrative names both, citing Jolivet 2023.
- If a newer EarthByte release supersedes Muller 2019, the pipeline is re-run and this ADR is superseded, not edited.
