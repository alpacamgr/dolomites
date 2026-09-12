# Plate-tectonic reconstruction data for the Dolomites / Adria (300 Ma – present)

Draft, 2026-09-06. Marker convention: `[verified 2026-09-06]` = fetched today; `[from search, not opened]` = seen only in search snippets; `[unverified - from memory]` = general geology stated from memory.

## 1. Purpose

Machine-readable datasets that can drive an animated map or globe of the Adria microplate / Southern Alps and the opening & closing of the Tethys oceans between ~300 Ma and today. Focus on files that a web front-end can consume directly (GPML, .rot for the GPlates Web Service; NetCDF/GeoTIFF for rasters; GeoJSON / shapefile for reconstructed geometries).

## 2. Global GPlates models

All EarthByte global models below are hosted on Zenodo with DOIs. The Zenodo records checked (Müller 2019, Merdith 2021, Müller 2022, Scotese PaleoDEM) are each released under **CC BY 4.0** [verified 2026-09-06]. Individual dataset pages are cited in Sources.

### 2.1 Müller et al. 2019 (deforming plate model)

| Field | Value |
|-------|-------|
| Full authors | Müller, Zahirovic, Williams, Cannon, Seton, Bower, Tetley, Heine, Le Breton, Liu, Russell, Yang, Leonard, Gurnis |
| Year | 2019 (v3.0 archived on Zenodo 2024) |
| Range | 250 – 0 Ma |
| Reference frame | Mantle; deforming plates |
| Formats | `.rot`, `.gpml`/`.gpmlz`, NetCDF age-grids, animation files |
| Age grids | 1 Myr time step; NetCDF at ~6 arc-min resolution [verified 2026-09-06 via search snippet on EarthByte seafloor-age page] |
| Volume | ~481 MB compressed |
| License | CC BY 4.0 |
| DOI | 10.5281/zenodo.10525286 |
| GWS id | `MULLER2019` |
| Notes | Includes lithospheric deformation since Pangea breakup (~240 Ma). Le Breton is a co-author; the model's Alpine sector is aligned with Le Breton et al. 2021 (see 3.1). v2.0 released 2020-02-20, superseding the original 2019 release (Young et al. 2018 kinematics for East Asia; Torsvik 2019 absolute plate motions; near-neighbour interpolation for deformation grids). [verified 2026-09-06 https://www.earthbyte.org/update-to-the-muller-et-al-2019-plate-reconstructions/] |

[verified 2026-09-06 https://zenodo.org/records/10525286]

### 2.2 Müller et al. 2022 (1 Ga, tectonic-rules mantle reference frame)

| Field | Value |
|-------|-------|
| Authors | Müller, Flament, Cannon, Tetley, Williams, Cao, Bodur, Zahirovic, Merdith |
| Year | 2022 |
| Range | 1000 – 0 Ma |
| Formats | GPlates/pyGPlates model files, NetCDF-4 age grids (mantle and pmag frames), animations |
| License | CC BY 4.0 |
| DOI | 10.5281/zenodo.10297173 |
| Companion paper | Solid Earth 13, 1127–1159 (doi:10.5194/se-13-1127-2022) |
| GWS id | `MULLER2022` (default model of GPlates Web Service) |

[verified 2026-09-06]

### 2.3 Merdith et al. 2021 (1 Ga, paleomagnetic reference frame)

| Field | Value |
|-------|-------|
| Authors | Merdith, Williams, Collins, Tetley, Mulder, Blades, Young, Armistead, Cannon, Zahirovic, Müller |
| Year | 2021 |
| Range | 1000 – 0 Ma |
| Time step | 5 Ma for Pacific-Africa 250–83 Ma; variable elsewhere. Repo warns not to use for < 5 Ma or absolute-motion studies. |
| Formats | GPML, .rot, GPlates `.gproj`; includes coastlines, continents, cratons, static polygons, plate topologies (1000–410, 410–250, 250–0 Ma), paleomagnetic poles |
| License | CC BY 4.0 |
| DOI | 10.5281/zenodo.10346399 (updated record); original 10.5281/zenodo.4485738 |
| GWS id | `MERDITH2021` |
| Journal | Earth-Science Reviews 214, 103477 (2021) |

[verified 2026-09-06]

### 2.4 Other global models on Zenodo

Sourced from the EarthByte "Global and regional plate motion models" index [verified 2026-09-06]:

| Model | Authors | Year | Range (Ma) | Zenodo DOI |
|-------|---------|------|-----------|------------|
| Müller et al. 2016 | Müller, Seton, Zahirovic + 9 | 2016 | 230–0 | 10.5281/zenodo.10565444 |
| Matthews et al. 2016 | Matthews, Maloney, Zahirovic, Williams, Seton, Müller | 2016 | 410–0 | 10.5281/zenodo.10526156 |
| Seton et al. 2012 | Seton, Müller, Zahirovic + 8 | 2012 | 200–0 | 10.5281/zenodo.10596049 |
| Young et al. 2018 | Young, Flament, Maloney + 4 | 2018 | 410–0 | 10.5281/zenodo.10525369 |
| Zahirovic et al. 2022 | Zahirovic, Eleish, Doss + 6 | 2022 | 400–0 | 10.5281/zenodo.4729045 |
| Cao et al. 2024 | Cao, Collins, Pisarevsky + 4 | 2024 | 1800–0 | 10.5281/zenodo.11536686 |
| Müller et al. 2025 / Shirmard 2025 | 6 & 4 co-authors | 2025 | 1800–0 | 10.5281/zenodo.15233548 |
| Scotese 2016 | Scotese | 2016 | 1100–0 | 10.5281/zenodo.10596609 |
| Clennett et al. 2020 | Clennett + 7 | 2020 | 170–0 | 10.5281/zenodo.10348270 |
| Alfonso et al. 2024 | Alfonso, Müller, Mather, Anthony | 2024 | 170–0 | 10.5281/zenodo.11392268 |

Matthews et al. 2016 is the earliest "continuous late-Paleozoic to present-day global plate model" [verified 2026-09-06 https://gwsdoc.gplates.org/models/] and is the natural candidate whenever a single global model must span the full 300 Ma – 0 window.

## 3. Regional Mediterranean / Alpine models

### 3.1 Le Breton et al. 2021 (Piemont-Liguria basin)

| Field | Value |
|-------|-------|
| Authors | Le Breton, Brune, Ustaszewski, Zahirovic, Seton, Müller |
| Journal | Solid Earth 12, 885–913, doi:10.5194/se-12-885-2021 |
| License | CC BY 4.0 |
| Time steps in paper | 200, 164.7, 154, 145, 130, 83, 35, 20, 0 Ma |
| Adria treatment | Split into two plates — northern Adria (Ivrea) and southern Adria (Apulia) — along the Mattinata Fault, to remove overlap with Corsica-Sardinia. |
| Oceans modeled | Piemont-Liguria in four opening stages (max ~250 km of mature oceanic crust); "Neo-Tethys (also known as the Meliata–Maliac–Vardar Ocean)" mentioned but not the paper focus. |
| Regional coverage | Western/Central Alps, Mediterranean |
| Files | Distributed as an update layered onto the Müller et al. 2019 rotation/topology set, at https://www.earthbyte.org/webdav/ftp/Data_Collections/Muller_etal_2019_Tectonics/ |

[verified 2026-09-06 https://se.copernicus.org/articles/12/885/2021/]

### 3.2 van Hinsbergen 2020 (Gondwana Research, Mediterranean since Triassic)

- Full title: *Orogenic architecture of the Mediterranean region and kinematic reconstruction of its tectonic evolution since the Triassic.* Gondwana Research 81: 79–229 (2020). DOI reachable via ScienceDirect page https://www.sciencedirect.com/science/article/pii/S1342937X19302230 [from search, not opened].
- GPlates files: distributed via the same package as van Hinsbergen et al. 2021 (Nature Geoscience) zip, currently hosted on figshare at https://figshare.com/articles/dataset/van_Hinsbergen_NatureGeo_2021_GPlates_zip/13516727 [from search, not opened — the record returned HTTP 403 to WebFetch today].
- Related distribution: the author's own page geologist.nl/reconstructions/ ships `Mediterranean.gpml`, a master `.rot` file `190701_vanHinsbergen_master.rot`, and rotation files for many other regions; usage note on that page: "please give reference to the proper publications." [verified 2026-09-06]

### 3.3 Handy et al. 2010 (Earth-Science Reviews)

- Full title: *Reconciling plate-tectonic reconstructions of Alpine Tethys with the geological–geophysical record of spreading and subduction in the Alps.* Earth-Sci. Rev. 102: 121–158 (2010) [verified via mantleplumes.org PDF listing 2026-09-06].
- Key contribution: reconstruction of Alpine Tethys that "additionally invokes independent microplates whose motions are constrained primarily by the geological record" [from search snippet].
- **No GPlates release known to me.** The paper delivers published maps at time slices; would need manual digitisation to feed an animation.

### 3.4 Stampfli & Borel 2002

- *A plate tectonic model for the Paleozoic and Mesozoic constrained by dynamic plate boundaries and restored synthetic oceanic isochrons.* EPSL 196: 17–33 (2002). doi:10.1016/S0012-821X(01)00588-X [from search, not opened].
- Coined the modern "Alpine Tethys" usage (Valais + Piemont–Liguria) and treats Adria as a microplate with continental and oceanic parts between Europe, Iberia, and Africa [from search snippet]. Underpins many later regional models.
- Availability of machine-readable files: not confirmed from a primary source; often cited as a "basis" but not itself a downloadable GPML bundle [unverified].

### 3.5 Other regional / legacy sources named in the brief

| Source | Status |
|--------|--------|
| Schmid et al. 2004 / 2008 | Alpine tectonic maps, published as figures; no known GPML release [unverified - from memory]. |
| Dercourt et al. Peri-Tethys atlas (2000) | Print atlas; not machine-readable [unverified - from memory]. |
| Ziegler 1990 "Geological Atlas of Western and Central Europe" | Print atlas / Shell publication; not machine-readable [unverified - from memory]. |
| Golonka | Model layered into GPlates as `GOLONKA` (0–550 Ma); GWS notes it "does not work for any present-day ocean points" [verified 2026-09-06]. |
| Vissers & Meijer | Referenced in the paleomagnetic community; not confirmed as a downloadable model. |
| Deep Time Maps / Ron Blakey | Commercial paleogeographic **images** (raster/JPEG-class), not machine-readable plate models — no GPML, shapefile, or GeoTIFF distribution documented. Terms: "Maps are protected by copyright to Colorado Plateau Geosystems Inc … Maps must be purchased to use in any application, and no maps may be used or reproduced in any manner without written permission/license." Tiered pricing (Academic, Library, Museum/Park, Corporate, Individual, Book). Not compatible with a "no fabricated data" open-web pipeline unless a license is bought. [verified 2026-09-06 https://deeptimemaps.com/about-us/] |

## 4. PALEOMAP / Scotese products

### 4.1 PaleoDEM rasters (Scotese & Wright 2018)

| Field | Value |
|-------|-------|
| Full title | PaleoDEM Resource – Scotese & Wright (2018) |
| Coverage | 540 Ma – present, 5 Myr steps, 117 rasters |
| Resolutions | 1° × 1° (standard) and 0.1° × 0.1° (~6 arc-min; high-res set) |
| Formats | Plain text (lat, lon, elev), NetCDF, CSV |
| License | CC BY 4.0 |
| DOI | 10.5281/zenodo.5460860 |
| Version | v2, published 2018-08-01 |
| Download | EarthByte hosts a zip of the 1°×1° NetCDFs (Scotese_Wright_2018_Maps_1-88_1degX1deg_PaleoDEMS_nc.zip); high-res on Zenodo. |
| Method / caveats | Authors describe outputs as "estimates" of elevation of the land surface and ocean depth; the page does not attach explicit uncertainty bounds. Interpretive model, not measurement. |

[verified 2026-09-06 https://www.earthbyte.org/paleodem-resource-scotese-and-wright-2018/]

### 4.2 PALEOMAP PaleoAtlas for GPlates (Scotese)

- 91 paleogeographic maps as Time-Dependent Raster files, spanning Phanerozoic + late Neoproterozoic.
- Download: https://www.earthbyte.org/webdav/ftp/earthbyte/Scotese_PaleoAtlas_v3.zip
- License: not stated on the EarthByte landing page [verified 2026-09-06 https://www.earthbyte.org/paleomap-paleoatlas-for-gplates/].
- Extended range: PaleoDEMs 0–750 Ma exist as a companion product (mentioned in NOAA Science-On-a-Sphere catalogue) [from search, not opened].

### 4.3 Scotese 2016 rotation model

- Range 1100 – 0 Ma; distributed via EarthByte Zenodo mirror at 10.5281/zenodo.10596609; also served as `PALEOMAP` model on the GPlates Web Service.

## 5. Torsvik & Cocks (CEED, Oslo)

- *Earth History and Palaeogeography*, Torsvik & Cocks, Cambridge Univ. Press 2017. Companion downloads announced at http://www.earthdynamics.org/earthhistory/ [verified 2026-09-06] via a "Data & Software" link, but the underlying `Data_Software.html` page returned HTTP 404 on my fetch today — files may have been relocated.
- CEED plate-models index at http://www.earthdynamics.org/earthmodel/ [verified 2026-09-06] lists:
  - Continental model (Torsvik et al. 2014; Torsvik & Cocks 2017), 540–0 Ma
  - Paleozoic polygon set (Domeier & Torsvik 2014), 410–250 Ma
  - Mesozoic–Cenozoic polygon set (Torsvik et al. 2019), 250–0 Ma
  - Caledonian, Asian, and global polygon subsets.
- On the GPlates Web Service the same set is served as `TorsvikCocks2017`, 0–540 Ma, in both mantle and paleomagnetic reference frames.
- Formats and license per individual model page — not extracted in this pass.

## 6. GPlates Web Service (GWS)

- Endpoint: https://gws.gplates.org — documentation at https://gwsdoc.gplates.org.
- Endpoints [verified 2026-09-06 https://gwsdoc.gplates.org/]:
  - Reconstruct: `reconstruct_points`, `reconstruct_coastlines`, `reconstruct_static_polygons`, `reconstruct_feature_collection`, `reconstruct_file`, `motion_path`.
  - Rotation (compute rotation parameters for a plate ID).
  - Assign plate IDs to arbitrary points.
  - Topology (plate-boundary polygons, subduction zones).
  - Raster query (sample paleogeographic rasters at a given age).
- Default model: `MULLER2022` (docs warn that relying on the default may cause surprises when the default changes).
- License: page carries only a copyright notice ("Copyright © 2020-2026 The University of Sydney. All rights reserved."); no explicit reuse licence.
- Rate limits: not published on the docs pages fetched.
- Self-hosting: source at https://github.com/GPlates/gplates-web-service, distributed as Docker images. Main deployment is supported by NCI (Australia) under the AuScope programme.

### 6.1 pyGPlates and gplately

- `pyGPlates`: Python bindings for the GPlates engine — read / reconstruct GPML, apply rotation files, sample rasters. Distributed by the GPlates project.
- `gplately`: high-level wrapper on pyGPlates for reconstructions, kinematics, and plotting; GPL-2.0 licensed; installable via pip and conda-forge [verified 2026-09-06 https://github.com/GPlates/gplately]. v2.0 released July 2025.
- `Plate Model Manager` (inside gplately): downloads by model identifier, e.g. `pm_manager.get_model("Muller2019", ...)`.
- Also: `gwspy` — thin Python wrapper around the GWS HTTP API [from search, not opened].
- R equivalent: `rgplates` [from search, not opened https://gplates.github.io/rgplates/].

## 7. Paleolatitude calculators & APWPs

- **paleolatitude.org** — original calculator built on three global APWPs for the last 200 Myr, tailored for paleoclimate use. Underlying paper: van Hinsbergen et al. 2015, PLOS ONE 10: e0126946, "A Paleolatitude Calculator for Paleoclimate Studies" [verified 2026-09-06 for citation via search; site itself renders as an SPA and returned only a bare title to WebFetch — no API discoverable from the HTML shell].
- **Paleolatitude.org 3.0** announced 2025 as "a calculator for paleoclimate and paleobiology studies based on a new global paleogeography model" (van Hinsbergen and colleagues) [from search, not opened https://www.researchgate.net/publication/404298698].
- **APWP-online.org** — companion open-source environment for computing APWPs and relative palaeomagnetic displacements from site-level data; hosts a curated paleomagnetic database and computes a global APWP for the last 320 Ma [from search, not opened https://apwp-online.org; underlying paper Vaes et al. 2023, ESR, doi:10.1016/j.earscirev.2023.104547].

## 8. What these models can and cannot honestly show for the Dolomites

### 8.1 Scale

Every global model above is built at continental to sub-continental resolution. Rotation poles are defined for whole plates or, in the Alpine sector, for two Adria pieces at best (Le Breton 2021). The Dolomites area is ~100 km across — smaller than the smallest independent block in any published global model. Whatever lives inside "Adria" (Southern Alps, Trento Platform, Dolomites, Belluno Basin) is carried as passive geometry attached to a plate ID, not tracked as its own moving block.

The PaleoDEM rasters at 1° have ~110 km cell size — larger than the entire Dolomites — and at 0.1° a single cell is ~11 km, roughly the size of the Sella group. That is not enough to place individual Triassic reef platforms relative to each other.

### 8.2 What is honest to show

- Paleolatitude of Adria through time (from any pmag-anchored model: TorsvikCocks2017, Merdith2021, or the pmag frame of Müller 2022).
- Distance and rotation of Adria relative to Europe and Africa (Le Breton 2021, van Hinsbergen 2020, Handy 2010).
- Opening and closing of the Piemont-Liguria Ocean, with the caveat that maximum-width estimates cluster in the hundreds of km (~250 km in Le Breton 2021) — much narrower than a typical school-atlas "Tethys" drawing.
- Global paleo-coastlines at 5 Myr steps (Scotese PaleoDEM, PALEOMAP), suitable as a distant background layer.
- Sequence of Tethys events at continental scale: Palaeotethys closes across the Cimmerian collisions, Middle Triassic to Early Jurassic; Meliata-Maliac-Vardar opens Middle Triassic and closes Late Jurassic to Cretaceous; Alpine Tethys (Piemont-Liguria + Valais) opens Middle Jurassic and closes Late Cretaceous to Palaeogene [general Alpine geology, unverified - from memory].

### 8.3 What is NOT honest to show

- Local paleo-elevation of the Dolomites at any age — rasters interpolate over hundreds of km.
- Exact positions of specific Ladinian/Carnian reef platforms (Sciliar, Latemar, Sella) relative to each other — they sit inside a single grid cell of even the high-res PaleoDEM, and the current-day map of these platforms should not be inferred from a plate rotation.
- Precise moment of individual reef drowning or carbonate demise as a plate-tectonic event — these are basin-scale sedimentary responses, not directly resolved by the plate model.
- Ocean depths in the Alpine Tethys — model outputs give age-of-seafloor and inferred crustal age, not water depth.

### 8.4 Where the models disagree about Adria

Two long-standing camps, well summarised in Jolivet 2023 (C. R. Géoscience 355: 9–28, doi:10.5802/crgeos.198) [verified 2026-09-06]:

1. **Adria as an African promontory.** Argand 1924; Channell & Horvath 1976; Channell et al. 2022. They cite paleomagnetic data showing "no differential drift" between Adria and Africa; separation, if any, is by small pull-apart basins along left-lateral transforms.
2. **Adria as an independent microplate**, separated from Africa by an intervening oceanic domain (Mesogea / Ionian). Dercourt et al. 1986; Biju-Duval et al. 1977; van Hinsbergen et al. 2019/2020; Handy et al. 2010; Le Breton et al. 2021.

Jolivet 2023 notes that paleomagnetic error bars "encompass several hundred kilometres" so the data alone do not settle the question; ophiolite evidence from Cyprus and southern Turkey is used to argue for an oceanic basin. Reconstructions differ "dramatically in surface area of oceanic crust shown" — van Hinsbergen's models display a wide Alpine-Atlantic connection with extensive oceanic domains, while Angrand & Mouthereau (2021) show much less oceanic lithosphere and invoke mantle exhumation rather than full spreading. In practical terms, expect several hundred km of position uncertainty for Adria in the Cretaceous–Cenozoic across published models, and expect Le Breton 2021's two-Adria split (Ivrea + Apulia) not to be reproduced by any purely global model.

### 8.5 Recommended backbones

1. **Müller et al. 2019** as the global-scale animation backbone. It is the most-cited "modern" model with deforming plates, covers 250 – 0 Ma (already includes the Late Permian in the deforming reconstruction), is CC BY 4.0, is directly consumable by pyGPlates / gplately / GWS, and its Alpine sector was co-authored by Le Breton (so it is internally consistent with the regional Piemont-Liguria model). For the full 300 – 250 Ma tail, extend with either Matthews et al. 2016 (410 – 0 Ma) or Müller et al. 2022 (1000 – 0 Ma), which are both drawn from the same EarthByte lineage.
2. **Le Breton et al. 2021** as the regional overlay for the Dolomites-relevant part (Adria, Alpine Tethys) from 200 Ma to today. Same rotation-file lineage as Müller 2019, so the two combine cleanly.
3. For paleogeographic look-and-feel (coastlines, land vs sea, mountains) render **Scotese PaleoDEM 0.1°** as a NetCDF-based raster tile layer at 5-Myr slices — but label it "interpretive paleogeography," not measurement, and never zoom in past the ~10–100 km cell size.

## 9. Sources

Access date for all entries below: 2026-09-06.

- GPlates Web Service model list — https://gwsdoc.gplates.org/models/ [verified]
- GPlates Web Service root — https://gwsdoc.gplates.org/ [verified]
- EarthByte global & regional plate motion models index — https://www.earthbyte.org/category/resources/data-models/global-regional-plate-motion-models/ [verified]
- Müller et al. 2019, EarthByte landing page — https://www.earthbyte.org/muller-et-al-2019-deforming-plate-reconstruction-and-seafloor-age-grids-tectonics/ [verified]
- Müller et al. 2019, Zenodo record 10525286 (CC BY 4.0) — https://zenodo.org/records/10525286 [verified]
- Müller et al. 2019, model FTP tree — https://www.earthbyte.org/webdav/ftp/Data_Collections/Muller_etal_2019_Tectonics/ [verified]
- Müller et al. 2022, Zenodo record 10297173 (CC BY 4.0) — https://zenodo.org/records/10297173 [verified]
- Müller et al. 2022, Solid Earth paper — https://se.copernicus.org/articles/13/1127/2022/ [from search, not opened]
- Merdith et al. 2021, Zenodo record 10346399 (CC BY 4.0) — https://zenodo.org/records/10346399 [verified]
- Le Breton et al. 2021, Solid Earth (CC BY 4.0) — https://se.copernicus.org/articles/12/885/2021/ [verified]
- Le Breton et al. 2021, EarthByte landing — https://www.earthbyte.org/kinematics-and-extent-of-the-piemont-liguria-basin-implications-for-subduction-processes-in-the-alps/ [verified]
- van Hinsbergen 2020, Gondwana Research (ScienceDirect) — https://www.sciencedirect.com/science/article/pii/S1342937X19302230 [from search, not opened]
- van Hinsbergen personal reconstructions site — https://www.geologist.nl/reconstructions/ [verified]
- van Hinsbergen 2021 GPlates zip on figshare — https://figshare.com/articles/dataset/van_Hinsbergen_NatureGeo_2021_GPlates_zip/13516727 [from search; my fetch returned HTTP 403 today]
- Handy et al. 2010, Earth-Sci. Rev. PDF — https://www.mantleplumes.org/WebDocuments/Handy%20et%20al%202010%20(Alpine%20Tethys%20reconstruction%20Earth-Sci%20Rev).pdf [from search, not opened]
- Stampfli & Borel 2002, EPSL, doi:10.1016/S0012-821X(01)00588-X [from search, not opened]
- Scotese & Wright 2018, PaleoDEM, EarthByte page — https://www.earthbyte.org/paleodem-resource-scotese-and-wright-2018/ [verified]
- Scotese & Wright 2018, PaleoDEM, Zenodo record 5460860 (CC BY 4.0) — https://zenodo.org/records/5460860 [verified]
- Scotese PALEOMAP PaleoAtlas for GPlates — https://www.earthbyte.org/paleomap-paleoatlas-for-gplates/ [verified]
- Torsvik & Cocks, Earth History and Palaeogeography (book landing) — http://www.earthdynamics.org/earthhistory/ [verified; the linked `Data_Software.html` returns 404 today]
- CEED plate models index — http://www.earthdynamics.org/earthmodel/ [verified]
- gplately, GitHub (GPL-2.0) — https://github.com/GPlates/gplately [verified]
- gplates-web-service, GitHub (self-host) — https://github.com/GPlates/gplates-web-service [from search, not opened]
- paleolatitude.org — http://paleolatitude.org/ [attempted; SPA shell only, no content extractable]
- van Hinsbergen et al. 2015, PLOS ONE 10: e0126946 (paleolatitude calculator paper) [from search citation, not opened]
- Vaes et al. 2023 APWP paper — https://www.sciencedirect.com/science/article/pii/S0012825223002362 [from search, not opened]
- Paleolatitude.org 3.0 (2025) — https://www.researchgate.net/publication/404298698 [from search, not opened]
- Jolivet 2023, "Tethys and Apulia (Adria), 100 years of reconstructions", C. R. Géoscience 355: 9–28, doi:10.5802/crgeos.198 (CC BY 4.0) — https://comptes-rendus.academie-sciences.fr/geoscience/articles/10.5802/crgeos.198/ [verified]

## 10. Open questions / gaps

- Exact license for the PALEOMAP PaleoAtlas for GPlates (the Zenodo mirror of Scotese 2016 rotations is CC BY 4.0; the raster PaleoAtlas landing page does not state a licence — needs a direct check inside the zip).
- Whether the van Hinsbergen 2020 Gondwana Research GPlates package is a self-contained release or only distributed indirectly through the geologist.nl master rot / Mediterranean gpml pair.
- Deep Time Maps / Ron Blakey commercial terms — not fetched in this pass.
- Whether paleolatitude.org exposes a REST or Python API (SPA site did not surface one to WebFetch; a look at the calculator's GitHub source would settle it — repo not yet located).
- Precise plate IDs used for "Adria (Ivrea)" and "Adria (Apulia)" in Le Breton 2021 — would need to open the `.rot` file itself.
- Status of `Data_Software.html` on the earthdynamics.org site (404 today); Torsvik / Cocks rotation files may have moved to CEED archives or Cambridge supplementary materials.
- Full time step of Müller 2019 age grids confirmed at 1 Myr, ~6 arc-min NetCDF resolution, via an EarthByte snippet [verified 2026-09-06]; not confirmed against the Zenodo README directly.
- Whether any published GPlates model tracks the Southern Alps / Trento Platform as a distinct block — the working answer today is **no**; only Adria as a whole, and, in Le Breton 2021, its two-plate split, is resolved.
- Whether MULLER2019 as extended by Le Breton 2021 covers Meliata / Vardar with rotation poles, or only Piemont-Liguria — the paper text confirms it names Meliata-Maliac-Vardar only in passing.
