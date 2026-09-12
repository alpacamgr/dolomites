# Quaternary Glaciation and Deep-Time Climate Context — Data Catalogue

Research notes for a scroll-driven geological-history visualization of the Dolomites
(South Tyrol / Trentino / Belluno, Italy). No fabricated data.
Compiled 2026-09-06.

**URL provenance tags** used throughout:
- `[verified 2026-09-06]` — successfully fetched and inspected during this research
- `[from search, not opened]` — appeared in web-search results only
- `[unverified — from memory]` — recalled without a live check (avoided; noted if used)

---

## A. Quaternary glaciation of the Alps and Dolomites

### A.1 Seguinot et al. 2018 — Alpine ice-sheet simulations (PISM)

Seguinot, J., Ivy-Ochs, S., Jouvet, G., Huss, M., Funk, M., Preusser, F. (2018).
"Modelling last glacial cycle ice dynamics in the Alps." *The Cryosphere*, 12,
3265-3285. https://tc.copernicus.org/articles/12/3265/2018/ `[from search, not opened]`

Model: PISM (Parallel Ice Sheet Model), full Alpine arc, entire last glacial cycle
(120–0 ka). Runs at **1 km and 2 km** horizontal resolution. Three temperature
forcings (EPICA, GRIP, MD01-2444 Iberian SST) × two precipitation modes (constant
vs. palaeo-precipitation reduction), encoded in filenames as
`alpcyc.{res}.{forcing}.{precip}.…nc`.

Two companion Zenodo datasets, both CC-BY-4.0, both NetCDF, both by Seguinot et al.:

| Dataset | DOI / URL | Content | Size | Time step |
|---|---|---|---|---|
| Aggregated variables | 10.5281/zenodo.1423160 — https://zenodo.org/record/1423160 `[verified 2026-09-06]` | Time-integrated / time-reduced fields (`alpcyc.*.agg.nc`) plus glacial-erosion outputs (`alpero.*`) | 14 files, ~7.9 GB total volume across variants (a single 1 km agg file is ~12.6 MB; largest are larger) | n/a (aggregate) |
| Continuous variables | 10.5281/zenodo.1423176 — https://zenodo.org/record/1423176 `[verified 2026-09-06]` | Time-dependent glacier model output; per netCDF metadata includes ice thickness, velocity, surface elevation | 14 files, ~1.0 GB total | 10 yr scalar time-series; 1 000 yr spatial snapshots |

*Follow-ups worth citing on the timeline:*
- Seguinot & Delaney (2021), "Last-glacial-cycle glacier erosion potential in the
  Alps", *Earth Surface Dynamics* 9, 923.
  https://esurf.copernicus.org/articles/9/923/2021-discussion.html
  `[from search, not opened]` — time-integrated glacial-erosion field for the Alps
  120–0 ka. Companion Zenodo.
- Werner, Scherler, Leger, Jouvet, Winkelmann (2026), "Impact of spatial resolution
  on large-scale ice cover modelling of mountainous regions," *The Cryosphere* 20,
  2469. https://tc.copernicus.org/articles/20/2469/2026/ `[verified 2026-09-06]`
  Western Alps, IGM model runs 50 m → 2 km; finds simulations at 300 m and finer
  produce comparable ice extents (2 km underestimates thin ice on peaks, or
  overestimates thick ice fill in valleys, depending on setup — factor ~2.5 volume
  spread between 50 m and 2000 m). Model setup archived at
  https://doi.org/10.5281/zenodo.14275231 (Leger et al. 2025). CC-BY-4.0.
  Dolomites coverage not confirmed from abstract.

### A.2 Alpine LGM extent — regional maps and GIS

- **GLACIMONTIS (Flantua et al., 2026)** — "Mountain glacier extents at the Last
  Glacial Maximum," *Scientific Data*, DOI 10.1038/s41597-026-06841-z.
  https://www.nature.com/articles/s41597-026-06841-z `[from search, not opened;
  landing page fetch redirected to auth]`
  Global geodatabase; 15 014 individual glacier reconstructions from 209 studies
  across 271 mountain ranges; updates knowledge in 135 ranges, flags gaps in 71.
  Precedes as the direct successor to Ehlers/Gibbard 2011. Format / license /
  Dolomites-specific coverage not verified from a fetched landing page (Nature
  redirected to auth); check the Data Availability section of the paper before use.

- **Ehlers, Gibbard & Hughes (2011)** — *Quaternary Glaciations — Extent and
  Chronology: A Closer Look* (Developments in Quaternary Science vol. 15,
  Elsevier). Historically the reference LGM shapefile compilation for Europe.
  Digital shapefiles were distributed on a CD-ROM bundled with the printed book;
  not identified as an open online download. `[from search, not opened]`
  https://shop.elsevier.com/books/quaternary-glaciations-extent-and-chronology/ehlers/978-0-444-53447-7

- **Bini et al. (2009)** — "Switzerland during the Last Glacial Maximum,"
  1:500 000, published by swisstopo. Standard published LGM ice-extent map of
  the Swiss Alps and adjacent regions. Available for purchase (CHF ~30) from
  the swisstopo online shop. `[from search, not opened]`
  https://shop.swisstopo.admin.ch/en/maps/geological-maps/geomaps-500000
  No open GIS download of the Bini shapefile identified in this pass.

- **Ivy-Ochs et al. (2008)**, "Chronology of the last glacial cycle in the
  European Alps," *J. Quaternary Science* 23, 559-573. Alpine cosmogenic /
  radiocarbon chronology synthesis. `[from search, not opened]`
  Consensus: maximum extent 26-20 ka; terminal lobes lingered in the foreland
  until ~22-17 ka, then rapid retreat synchronous with mountain ice-surface
  lowering.

- **Monegato et al. (2007, 2017); Ravazzi et al. (2012)** — Tagliamento end-
  moraine amphitheatre (SE Alps): two-fold LGM advance culminations between
  26.5 and 23 cal ka BP. `[from search, not opened]`

- **Serrano et al. / Rossato and colleagues** on Valsugana LGM network (SE
  Prealps, close to the southern Dolomites): 10Be exposure ages of lateral
  moraines cluster 20-19 ka, meaning ice-surface lowering did not begin before
  ~19 ka in that sector. *Alpine and Mediterranean Quaternary Sciences Journal*
  74, 151 (2025). https://egqsj.copernicus.org/articles/74/151/2025/
  `[from search, not opened]`

### A.3 Dolomites-specific local glaciation

- **Adige/Etsch glacier system, Bolzano basin.** Piedmont lobe fed the Garda
  end-moraine system (GEMS); LGM accumulation area of the Adige-Sarca system
  was ~15 000 km²; ice thickness in the Bolzano area reached ~2 000 m
  (Dolomite valleys generally >1 500 m of ice). Transfluence from Adige to
  Piave via Gardena and San Pellegrino passes. `[from search, not opened;
  sources: Dolomiti UNESCO site (fetch refused HTTP 403), and Alpine LGM
  syntheses cited above]`

- **Bolzano bedrock morphology.** Fadel et al. (2024), *Pure and Applied
  Geophysics*, "Geophysical Investigation and 3D Modeling of Bedrock Morphology
  in an Urban Sediment-Filled Basin: The Case of Bolzano." — glacial-basin
  bedrock model useful for a "glacier over the city" visualization.
  https://link.springer.com/article/10.1007/s00024-024-03512-1 `[from search,
  not opened]`

- **Alta Badia (Eastern Dolomites) 36Cl exposure dating.** Rossato and
  colleagues (2025), *Geomorphology*, "Cosmogenic dating reveals the timing of
  glaciers collapse in the high Dolomites valleys (Northern Italy)."
  https://www.sciencedirect.com/science/article/pii/S0169555X25000583
  `[fetch refused HTTP 403; findings from search snippet]`
  Deglaciation after LGM begins ~17 ka in Alta Badia; Gschnitz readvance
  15.8-15.4 ka; Daun-equivalent readvance 14.4-13.3 ka.

- **Postglacial rock-slope failures (large landslides).**
  - Marocca Principale (Marocche di Dro complex, Sarca valley): ~1 000 × 10⁶ m³,
    5.3 ± 0.9 ka (some sources 5 300 ± 860 yr).
  - Molveno rockslide: ~600 × 10⁶ m³, 4.8 ± 0.5 ka.
  - Lavini di Marco (Adige valley near Rovereto): ~200 × 10⁶ m³, 3.0 ± 0.4 ka
    (36Cl exposure ages 2.6-5.4 ka span polyphase movement).
  - Kas event (Marocche complex): 1080 ± 160 yr ago.
  Key reference: Ivy-Ochs et al. (2013), "Lavini di Marco (Trentino, Italy):
  36Cl exposure dating of a polyphase rock avalanche."
  https://www.sciencedirect.com/science/article/abs/pii/S1871101413000733
  Synthesis: Rossato et al. (2018), "Post-LGM catastrophic landslides in the
  Dolomites: when, where and why."
  https://www.aiqua.it/images/upload/20180510231242_Rossato-et-al_Landslides-Dolomites.pdf
  All `[from search, not opened]`. Note: these events are Holocene, not
  syn-deglacial — earlier claims of LGM-age triggering have been overturned.

### A.4 Present-day and historical glaciers

- **The Cryosphere synthesis, Dolomites, 2025.** Securo, Del Gobbo, Baccolo,
  Barbante, Citterio, De Blasi, Marcer, Valt, Colucci (2025), "The glaciers
  of the Dolomites: the last 40 years of melting," *The Cryosphere* 19, 1335.
  https://tc.copernicus.org/articles/19/1335/2025/ `[verified 2026-09-06]`
  - Area 4.11 → 1.81 km² (−56%); 33% of loss in 2010-2023 alone.
  - Volume −0.105 Gt total; −0.022 Gt since 2010.
  - Mean mass balance −0.64 ± 0.06 m w.e./yr.
  - Processed datasets on Zenodo: https://doi.org/10.5281/zenodo.11109783
  - Raw lidar / weather data "available upon request to ARPAV".
  - Archival imagery via a regional repository. CC-BY-4.0.

- **Marmolada glacier** — 2020 volume ~0.03 km³; 2004-2014 lost ~30% ice
  volume, ~22% area; small ice-collapse event 3 July 2022 (~70 400 m³
  detached mass — the fatal ice avalanche); projected mostly gone by ~2034
  under 2.7 °C warming. Sources include the NHESS 2024 preprint on the 2022
  collapse: https://nhess.copernicus.org/preprints/nhess-2024-212/
  `[from search, not opened]` — should be cross-checked before publication;
  Marmolada is the Dolomites' largest glacier and its shrinkage numbers are
  a key headline stat.

- **Little Ice Age (LIA) Alpine reconstructions.** Reinthaler & Paul (2025),
  "Reconstructed glacier area and volume changes in the European Alps since
  the Little Ice Age," *The Cryosphere* 19, 753. `[verified 2026-09-06]`
  https://tc.copernicus.org/articles/19/753/2025/
  - Covers full Alps in 14 sub-regions, explicitly including "Dolomites, Carnic
    Alps, and Julian Alps" and Southern Rhaetian Alps.
  - LIA (~1850) → 2015: area 4 244 → 1 806 km² (−57%); volume 280 ± 43 →
    100 ± 17 km³ (−64%); mean surface lowering −43.7 m; ≥1 938 glaciers
    completely melted.
  - Data (LIA outlines, reconstructed surface DEMs at 30 m, bed elevations,
    ice-thickness grids) on Zenodo: https://doi.org/10.5281/zenodo.14336826
    CC-BY-4.0.
  - Companion (Alps-wide 3D LIA reconstruction, higher resolution): Bühler et
    al. (2025), *The Cryosphere* 19, 5913. https://tc.copernicus.org/articles/19/5913/2025/
    `[from search, not opened]`

- **RGI 7.0 (Randolph Glacier Inventory).** RGI Consortium (2023), NSIDC-0770
  v7. DOI: https://doi.org/10.5067/F6JMOVY5NAVZ `[from search, not opened]`
  User guide: https://www.glims.org/rgi_user_guide/welcome.html
  Global glacier outlines, target date ~year 2000; the Alps are in RGI region
  11 (Central Europe). Format: shapefiles / GeoPackage per region.

- **GLIMS** database of glacier outlines, including 67 nominal Dolomite
  glaciers seeded from WGI-XF. Downloads at
  https://www.glims.org/maps/download in ESRI shapefile / MapInfo / GML / KML.
  `[from search, not opened]`

- **Nuovo Catasto dei Ghiacciai Italiani** — Smiraglia & Diolaiuti (eds., 2015;
  Comitato Glaciologico Italiano / Univ. Milano). 903 glaciers, 369.90 km²
  total. PDF hosted by CGI at
  https://glaciologia.it/catasto-dei-ghiacciai-italiani-cura-c-smiraglia-g-diolaiuti/
  `[from search, not opened]`. Underlying orthophotos 2005-2011. Not an open
  GIS release; check licensing before redistribution.

- **South Tyrol GIS-based LIA reconstruction** — Knoll & Kerschner (2010?),
  "A GIS-based Reconstruction of Little Ice Age Glacier Maximum Extents for
  South Tyrol, Italy" — 310 glaciers. `[from search, not opened]`

- **Monitoring bodies.** Annual campaign reports and glacier front-variation
  data:
  - Comitato Glaciologico Italiano (CGI): https://glaciologia.it/
  - ARPAV (Veneto regional environmental agency): Marmolada campaigns
  - Provincia Autonoma di Trento
  - South Tyrol / Provincia Autonoma di Bolzano glacier cadastre
  Open data availability varies; some products require request.

### A.5 Uplift, exhumation, erosion

- **Thermochronological transect across the Trento platform (Eastern Southern
  Alps).** Recent *Swiss Journal of Geosciences* paper (2025) — onset of
  exhumation ~25 Ma; peak exhumation rates 17-10 Ma; late-Miocene
  Adamello rapid exhumation ~0.65 km/Myr from ~8 Ma; Pliocene rate low
  in that sector.
  https://link.springer.com/article/10.1186/s00015-025-00491-w
  `[from search, not opened]`

- **Alpine-wide late-Neogene exhumation review.** Fox et al. and others —
  more than 2× increase since Late Miocene, potentially climate-driven.
  https://www.researchgate.net/publication/224962543_Late_Neogene_Erosion_of_the_Alps_A_Climate_Driver
  `[from search, not opened]`

- **Present-day GNSS uplift.** Sánchez, Völksen, Sokolov, Arenz, Seitz (2018),
  "Present-day surface deformation of the Alpine region inferred from
  geodetic techniques," *Earth System Science Data* 10, 1503-1523.
  https://essd.copernicus.org/articles/10/1503/2018/ `[verified 2026-09-06]`
  - Data on PANGAEA (ALPS2017): https://doi.pangaea.de/10.1594/PANGAEA.886889
  - Products: multi-year SINEX solution, station cartesian/ellipsoidal
    coordinates and velocities, gridded horizontal & vertical deformation
    (25 × 25 km, `ALPS2017_DEF_HZ.GRD`, `ALPS2017_DEF_VT.GRD`), continuous
    velocity field grid, strain field grid.
  - Southern Eastern Alps vertical uplift ~1.0-1.5 mm/yr (higher in Austrian
    Alps interior >2 mm/yr); shortening ~2 mm/yr across the southern front
    (Venetian-Friuli).
  - CC-BY-4.0.
- Related: Serpelloni et al. (2022), "Common-mode signals and vertical
  velocities in the greater Alpine area from GNSS data," *Solid Earth* 13,
  1541. https://se.copernicus.org/articles/13/1541/2022/ `[from search, not
  opened]`

---

## B. Deep-time context curves

### B.6 Sea level

| Interval | Reference | Data location | Notes |
|---|---|---|---|
| Full Cenozoic (0-66 Ma), *relative to modern* | Miller et al. (2020), *Science Advances* 6, eaaz1346, "Cenozoic sea-level and cryospheric evolution from deep-sea geochemical and continental margin records." | PANGAEA raw curve: https://doi.pangaea.de/10.1594/PANGAEA.923126 · smoothed: https://doi.pangaea.de/10.1594/PANGAEA.923139 · NOAA text mirror: https://www.ncei.noaa.gov/pub/data/paleo/contributions_by_author/miller2020/miller2020rsl-noaa.txt | `[from search, not opened]` License: PANGAEA data usually CC-BY. Confirm on landing page. |
| Late Pleistocene (0-800 ka) sea-level stack | Spratt & Lisiecki (2016), *Climate of the Past* 12, 1079. | NOAA WDS Paleoclimatology: https://www.ncei.noaa.gov/pub/data/paleo/contributions_by_author/spratt2016/ · Paper DOI 10.5194/cp-12-1079-2016 · Updated v2 (2025) on PANGAEA: https://doi.pangaea.de/10.1594/PANGAEA.979830 | `[from search, not opened]` PC1 of seven records; ~80% of variance in glacial-interglacial signal. NOAA release DOI 10.25921/RD66-5820. |
| Mesozoic long-term & short-term | Haq (2014), "Cretaceous eustasy revisited," *Global and Planetary Change* 113, 44-58. Haq (2018), Triassic eustasy (*GSA Today*). Haq, Hardenbol, Vail (1987) — historical baseline. | Haq 1987 open PDF: https://www.mantleplumes.org/WebDocuments/Haq1987.pdf · Haq 2018 Triassic *GSA Today* article: https://rock.geosociety.org/net/gsatoday/science/G381A/article.htm · Community digitizations, e.g. Figshare: https://figshare.com/articles/dataset/Haq_sea_level_curve/1005016 | `[from search, not opened]` The Haq curves are widely criticized in absolute amplitude; usable as a shape guide, not a metric. Be explicit in the UI. |

### B.7 Global temperature and CO2

| Interval | Reference | Data | Notes |
|---|---|---|---|
| Cenozoic 0-66 Ma benthic δ¹⁸O / δ¹³C reference | Westerhold et al. (2020), *Science* 369, 1383, "An astronomically dated record of Earth's climate…" (CENOGRID). | PANGAEA: https://doi.pangaea.de/10.1594/PANGAEA.917503 `[from search, not opened]` | Resolution: 2 kyr avg. for 0-34 Ma, 4.4 kyr for 34-67 Ma. Splice of 14 ODP/IODP sites. Defines Hothouse / Warmhouse / Coolhouse / Icehouse states. CC-BY. |
| Phanerozoic 540 Ma temperature (proxy compilation) | Scotese, Song, Mills, van der Meer (2021), *Earth-Science Reviews* 215, 103503, "Phanerozoic paleotemperatures." | Preprint / accepted manuscript at White Rose repo: https://eprints.whiterose.ac.uk/id/eprint/169823/ | `[from search, not opened]` Supplementary Table S2 in the ScienceDirect record holds the temperature curve. Confirm licensing before redistribution. |
| Phanerozoic 485 Ma GMST via data assimilation | Judd, Tierney, Lunt, Montañez, Huber, Wing, Valdes (2024), *Science* 385, "A 485-million-year history of Earth's surface temperature" (PhanDA). | Code + output on GitHub: https://github.com/EJJudd/PhanDA `[verified 2026-09-06]` — `5_Outputs/PhanDA_GMSTandCO2_percentiles.csv` (5th, 16th, 50th, 84th, 95th percentile GMST and CO2); `5_Outputs/LTG_percentiles/` (85 time slices of latitudinal T gradient); `PhanDA_GMST_ensemble.mat` (full ensemble). Model priors on Zenodo (2.1 TB!): https://doi.org/10.5281/zenodo.8237751 (17 440 HadCM3L netCDF files, CC-BY-4.0). PhanSST proxies: https://doi.org/10.5281/zenodo.7049233 | 85 assimilated time slices, ~5-Myr avg. spacing over 485 Ma. GMST spans 11-36 °C across the Phanerozoic. Best modern reconstruction to use as the temperature curve for a deep-time timeline. |
| Phanerozoic CO2 (multi-proxy) | Foster, Royer, Lunt (2017), *Nature Communications* 8, 14845, "Future climate forcing potentially without precedent in the last 420 million years." | Paper (open access): https://www.nature.com/articles/ncomms14845 `[from search, not opened]` — the LOESS-fit CO2 record is bundled as supplementary information; the download link was not verified in this pass. | Multi-proxy 420 Ma LOESS fit with 95% CI. CC-BY-4.0 through Nature Comms. |
| Cenozoic CO2 (66-0 Ma, community reconstruction) | The CenCO2PIP Consortium — Hönisch et al. (2023), "Toward a Cenozoic history of atmospheric CO2," *Science* 382, eadi5177. | Vetted data hub: https://paleo-co2.org/ `[from search, not opened]` — 5 698 individual paleo-CO2 estimates, quality-flagged and re-scaled where necessary. | Should be preferred over older Cenozoic CO2 compilations for the 66-0 Ma stretch. Not fetched to verify license text; expect CC-BY. |

### B.8 Paleolatitude of the Dolomites

- **paleolatitude.org 3.0** — van Hinsbergen, Vaes, Boschman, Paridaens, Bijl,
  Cramwinckel, Hermans and co-authors (2026 preprint, replacing the 2015 tool).
  Preprint: https://eartharxiv.org/repository/view/11411/ `[verified 2026-09-06]`
  - First global paleogeographic model back to 320 Ma, including GPlates
    reconstruction files.
  - Batch computation + CSV / graph export in the web UI; no explicit REST API
    mentioned in the preprint.
  - License: CC-BY-4.0.
  - Adria/Southern Alps handling not explicitly detailed in the preprint
    excerpt — plate-ID selection is part of the tool workflow; for a Dolomites
    point (~46.5°N, 11.8°E) use the Adria (or Africa where Adria not defined)
    plate.
- Original tool: van Hinsbergen et al. (2015), *PLOS ONE* 10, e0126946,
  "A Paleolatitude Calculator for Paleoclimate Studies." `[from search, not
  opened]` https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0126946

**Triassic-specific paleomagnetism of the Southern Alps / Adria:**
- Muttoni, Kent, Channell (1996), "Evolution of Pangea: paleomagnetic
  constraints from the Southern Alps, Italy," *Earth and Planetary Science
  Letters*. https://www.sciencedirect.com/science/article/pii/0012821X96000386
  `[from search, not opened]`
- Muttoni et al. (2013), "The drift history of Adria and Africa from 280 Ma to
  Present, Jurassic true polar wander, and zonal climate control on Tethyan
  sedimentary facies," *Palaeogeography, Palaeoclimatology, Palaeoecology*.
  `[from search, not opened]`
- Muttoni & Kent (2019), "Jurassic Monster Polar Shift Confirmed by Sequential
  Paleopoles From Adria, Promontory of Africa," *JGR: Solid Earth*.
  https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2018JB017199 `[from
  search, not opened]`

Consistent picture: the Dolomites (as part of the Trento Plateau / Adria
promontory) moved coherently with Africa since at least the Permian; sat at
~10-15°N in the Middle Triassic (site of the Dolomite reef platforms in the
western Tethys tropics) — quantitative paleolatitudes should be pulled from
paleolatitude.org 3.0 rather than quoted from memory here.

### B.9 Mass extinctions and GSSPs relevant to the Dolomites record

**GSSPs in / near the Dolomites (from https://stratigraphy.org/gssps/ `[verified
2026-09-06]`):**

| Boundary (stage base) | Section | Region | Ratified | Primary marker |
|---|---|---|---|---|
| Ladinian (Middle Triassic base) | Bagolino, Prov. Brescia | Southern Alps (western sector, not the Dolomites proper) | 2005 | Base of limestone above "Chiesense groove"; FAD of ammonoid *Eoprotrachyceras curionii*. Age ~241 Ma (U-Pb single-zircon on volcaniclastics). |
| Carnian (Upper Triassic base) | Prati di Stuores / Stuores Wiesen | Eastern Dolomites, Badia valley | 2008 | Base of bed SW4 in San Cassiano Fm.; FAD of ammonoid *Daxatina canadensis*; near-FAD of conodont *Quadralella (Paragondolella) polygnathiformis*. |
| Priabonian (Upper Eocene base) | Alano section, Piave River | Veneto Prealps, Belluno province | 2020 | *Included because the section lies in the Belluno pre-Dolomites and can anchor a Cenozoic tie-point in the visualization.* |

**Boundary events recorded (or partially recorded) in the Dolomites:**

- **Permian–Triassic boundary.** GSSP itself is Meishan (China). Dolomite
  reference sections in the western Dolomites: **Tesero** (Val di Fiemme) and
  **Bulla / Pufels** (Val Badia), where the top of the Bellerophon Fm. passes
  into the Werfen Fm. (Tesero horizon = topmost Permian; base of Triassic
  defined at FAD of *Hindeodus parvus*, within the Mazzin Member). Well-known
  strontium-isotope, palynological, magnetostratigraphic, and carbonate-crisis
  records exist. `[from search, not opened]`

- **Carnian Pluvial Episode (CPE), ~234-232 Ma.** Type region for the CPE is
  literally the Dolomites — the "termination of carbonate slope progradation"
  in the Cassian Dolomite / San Cassiano Fm. is one of the classic signals.
  Reference locality: Tofane area near Cortina d'Ampezzo. Marine turnover
  (ammonoids, conodonts) + terrestrial floral/vertebrate change; ~33% of
  marine genera disappear per one meta-analysis. Key refs: Dal Corso et al.
  (2020), "Extinction and dawn of the modern world in the Carnian," *Science
  Advances* 6, eaba0099.
  https://www.science.org/doi/10.1126/sciadv.aba0099 `[from search, not opened]`
  Preto et al. (Cortina/Tofane): https://www.natura.museum/wp-content/uploads/2020/05/GeoAlp_006_0080-0115.pdf

- **End-Triassic mass extinction (~201 Ma).** Preserved in the Dolomites'
  overlying successions (post-Dolomia Principale). Not a GSSP here; the base
  of the Jurassic GSSP is at Kuhjoch, Austria.

---

## Sources (consolidated)

Access date for every URL below is **2026-09-06**. Where the license is not
stated, it was not verified in this research pass and should be re-checked
before use.

**A.1 — Alpine ice-sheet simulations**
- Seguinot, J., Ivy-Ochs, S., Jouvet, G., Huss, M., Funk, M. & Preusser, F.
  (2018). *The Cryosphere* 12, 3265-3285.
  https://tc.copernicus.org/articles/12/3265/2018/ `[from search, not opened]`
- Seguinot et al. (2018) Zenodo, aggregated variables.
  https://zenodo.org/record/1423160 · DOI 10.5281/zenodo.1423160 · CC-BY-4.0
  `[verified]`
- Seguinot et al. (2018) Zenodo, continuous variables.
  https://zenodo.org/record/1423176 · DOI 10.5281/zenodo.1423176 · CC-BY-4.0
  `[verified]`
- Seguinot & Delaney (2021). *Earth Surface Dynamics* 9, 923.
  https://esurf.copernicus.org/articles/9/923/2021-discussion.html
  `[from search, not opened]`
- Werner et al. (2026). *The Cryosphere* 20, 2469.
  https://tc.copernicus.org/articles/20/2469/2026/ · CC-BY-4.0 `[verified]`
- Leger et al. (2025) IGM model setup. Zenodo DOI 10.5281/zenodo.14275231
  `[from search, not opened]`

**A.2 — LGM extent maps**
- Flantua et al. (2026) GLACIMONTIS. *Scientific Data*.
  DOI 10.1038/s41597-026-06841-z ·
  https://www.nature.com/articles/s41597-026-06841-z `[from search, not opened
  — Nature landing page fetch redirected to auth]`
- Ehlers, Gibbard & Hughes (2011). *Quaternary Glaciations — Extent and
  Chronology: A Closer Look*, Elsevier. (Shapefile CD only.)
  `[from search, not opened]`
- Bini et al. (2009) swisstopo LGM 1:500 000 map.
  https://shop.swisstopo.admin.ch/en/maps/geological-maps/geomaps-500000
  `[from search, not opened]`
- Ivy-Ochs et al. (2008). *J. Quaternary Science* 23, 559-573. `[from search,
  not opened]`
- Monegato et al. (2007). *Quaternary Research* 68 (2007). `[from search, not
  opened]`
- Rossato et al. (2025) Valsugana LGM. *Alpine and Mediterranean Quaternary
  Sciences Journal* 74, 151.
  https://egqsj.copernicus.org/articles/74/151/2025/ `[from search, not opened]`

**A.3 — Dolomites deglaciation, nunataks, landslides**
- Dolomiti UNESCO site (fetch refused HTTP 403 during this research):
  https://www.dolomitiunesco.info/en/the-dolomites-unesco-world-heritage-site/outstanding-universal-value/geology/glaciers-of-the-dolomites
  `[fetch failed 2026-09-06]`
- Fadel et al. (2024), Bolzano bedrock morphology, *Pure and Applied
  Geophysics*.
  https://link.springer.com/article/10.1007/s00024-024-03512-1 `[from search,
  not opened]`
- Rossato et al. (2025), Cosmogenic dating of Alta Badia deglaciation.
  https://www.sciencedirect.com/science/article/pii/S0169555X25000583
  `[fetch refused HTTP 403]`
- Ivy-Ochs et al. (2013), Lavini di Marco.
  https://www.sciencedirect.com/science/article/abs/pii/S1871101413000733
  `[from search, not opened]`
- Rossato et al. (2018), Post-LGM catastrophic landslides in the Dolomites.
  https://www.aiqua.it/images/upload/20180510231242_Rossato-et-al_Landslides-Dolomites.pdf
  `[from search, not opened]`

**A.4 — Present-day and historical glaciers**
- Securo et al. (2025). *The Cryosphere* 19, 1335.
  https://tc.copernicus.org/articles/19/1335/2025/ · Data:
  https://doi.org/10.5281/zenodo.11109783 · CC-BY-4.0 `[verified]`
- Bosin, Boaga et al. (2024) NHESS preprint on the 2022 Marmolada collapse.
  https://nhess.copernicus.org/preprints/nhess-2024-212/ `[from search, not
  opened]`
- Reinthaler & Paul (2025). *The Cryosphere* 19, 753.
  https://tc.copernicus.org/articles/19/753/2025/ · Data:
  https://doi.org/10.5281/zenodo.14336826 · CC-BY-4.0 `[verified]`
- Bühler et al. (2025), Alps-wide 3D LIA reconstruction. *The Cryosphere* 19,
  5913. https://tc.copernicus.org/articles/19/5913/2025/ `[from search, not
  opened]`
- RGI Consortium (2023). RGI 7.0 at NSIDC. DOI 10.5067/F6JMOVY5NAVZ.
  https://www.glims.org/rgi_user_guide/welcome.html `[from search, not opened]`
- GLIMS Glacier Database download.
  https://www.glims.org/maps/download `[from search, not opened]`
- Smiraglia & Diolaiuti (eds., 2015). *Nuovo Catasto dei Ghiacciai Italiani*.
  Comitato Glaciologico Italiano.
  https://glaciologia.it/catasto-dei-ghiacciai-italiani-cura-c-smiraglia-g-diolaiuti/
  `[from search, not opened]`
- Knoll & Kerschner, South Tyrol LIA GIS reconstruction.
  https://www.researchgate.net/publication/220606069 `[from search, not opened]`

**A.5 — Uplift**
- Thermochronology across Trento Platform (2025). *Swiss J. Geosci.*
  https://link.springer.com/article/10.1186/s00015-025-00491-w `[from search,
  not opened]`
- Sánchez et al. (2018). *Earth System Science Data* 10, 1503.
  https://essd.copernicus.org/articles/10/1503/2018/ · Data:
  https://doi.pangaea.de/10.1594/PANGAEA.886889 · CC-BY-4.0 `[verified]`
- Serpelloni et al. (2022). *Solid Earth* 13, 1541.
  https://se.copernicus.org/articles/13/1541/2022/ `[from search, not opened]`

**B.6 — Sea level**
- Miller et al. (2020). *Science Advances* 6, eaaz1346.
  PANGAEA: https://doi.pangaea.de/10.1594/PANGAEA.923126 and
  https://doi.pangaea.de/10.1594/PANGAEA.923139 · NOAA:
  https://www.ncei.noaa.gov/pub/data/paleo/contributions_by_author/miller2020/miller2020rsl-noaa.txt
  `[from search, not opened]`
- Spratt & Lisiecki (2016). *Climate of the Past* 12, 1079.
  https://www.clim-past.net/12/1079/2016/ · NOAA data:
  https://www.ncei.noaa.gov/pub/data/paleo/contributions_by_author/spratt2016/ ·
  Updated v2 (2025) PANGAEA: https://doi.pangaea.de/10.1594/PANGAEA.979830
  `[from search, not opened]`
- Haq et al. (1987) — https://www.mantleplumes.org/WebDocuments/Haq1987.pdf ·
  Haq (2014, 2018). `[from search, not opened]`

**B.7 — Temperature and CO2**
- Westerhold et al. (2020) CENOGRID. PANGAEA:
  https://doi.pangaea.de/10.1594/PANGAEA.917503 `[from search, not opened]`
- Scotese et al. (2021), *Earth-Science Reviews* 215, 103503.
  https://eprints.whiterose.ac.uk/id/eprint/169823/ `[from search, not opened]`
- Judd et al. (2024) PhanDA. GitHub:
  https://github.com/EJJudd/PhanDA `[verified]` · Model priors Zenodo:
  https://doi.org/10.5281/zenodo.8237751 (CC-BY-4.0, 2.1 TB) `[verified]` ·
  PhanSST: https://doi.org/10.5281/zenodo.7049233 · Paper:
  https://www.science.org/doi/10.1126/science.adk3705 `[from search, not opened]`
- Foster, Royer, Lunt (2017). *Nature Communications* 8, 14845.
  https://www.nature.com/articles/ncomms14845 `[from search, not opened]`
- CenCO2PIP / Hönisch et al. (2023), *Science* 382, eadi5177. Data hub:
  https://paleo-co2.org/ `[from search, not opened]`

**B.8 — Paleolatitude**
- van Hinsbergen et al. (2015), *PLOS ONE* 10, e0126946.
  https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0126946
  `[from search, not opened]`
- van Hinsbergen et al. (2026 preprint) paleolatitude.org 3.0.
  https://eartharxiv.org/repository/view/11411/ · CC-BY-4.0 `[verified]`
- Muttoni, Kent, Channell (1996). *EPSL*.
  https://www.sciencedirect.com/science/article/pii/0012821X96000386
  `[from search, not opened]`
- Muttoni et al. (2013). *Palaeogeography, Palaeoclimatology, Palaeoecology*.
  `[from search, not opened]`
- Muttoni & Kent (2019). *JGR: Solid Earth*.
  https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2018JB017199 `[from
  search, not opened]`

**B.9 — GSSPs and boundary events**
- International Commission on Stratigraphy, GSSP list.
  https://stratigraphy.org/gssps/ `[verified]`
- ICS Carnian GSSP document.
  https://stratigraphy.org/gssps/files/carnian.pdf `[from search, not opened]`
- Dal Corso et al. (2020), CPE. *Science Advances* 6, eaba0099.
  https://www.science.org/doi/10.1126/sciadv.aba0099 `[from search, not opened]`

---

## Open questions / gaps

1. **Seguinot NetCDF variable inventory.** The Zenodo landing pages confirm
   the presence of ice-thickness / velocity / surface-elevation variables in
   the continuous-variable files but do not list every variable in this
   research pass. Download one file and inspect its NetCDF header before
   committing to a specific field in the visualization.
2. **Bini 2009 GIS layers.** The published shapefiles behind the swisstopo
   1:500 000 map do not appear to be openly downloadable; contact swisstopo
   or use GLACIMONTIS (2026) as the open alternative.
3. **GLACIMONTIS Alps coverage details** were not verified from a fetched
   landing page (Nature redirected to auth). Confirm that the Dolomites are
   included in one of the 271 mountain ranges, and confirm the license, before
   citing.
4. **Marmolada volume time-series.** Numbers cited (2020 volume, 2004-2014
   loss, 2022 collapse mass) come from search snippets, not fetched papers.
   The Bosin et al. NHESS 2024 preprint should be fetched and its Fig./Table
   of area & volume through time transcribed.
5. **Ehlers/Gibbard 2011 shapefile licensing.** The CD-ROM shapefiles have an
   Elsevier attribution; whether they can be redistributed inside a public
   visualization has to be checked against Elsevier's terms.
6. **Nuovo Catasto GIS layers.** The 2015 CGI inventory is a PDF release; a
   companion GIS release exists in various forms but its license was not
   verified here.
7. **paleolatitude.org 3.0 batch/API details.** The 2026 preprint mentions
   batch computation and export functions but no formal REST API. If we want
   scriptable access, we may need to reproduce the pole-rotation math offline
   using the published GPlates reconstruction files.
8. **Foster et al. 2017 CO2 supplement location.** The paper is open access on
   Nature; the actual XLSX/CSV in the supplement was not fetched here.
9. **CenCO2PIP license.** paleo-co2.org was not fetched to confirm the exact
   licence attached to the compilation.
10. **Late-glacial and Holocene chronology of the Dolomites** (Younger Dryas
    readvances, Egesen, 8.2 ka event, Neoglacial, Alpine cirque glaciers)
    needs a dedicated pass — this catalogue only touches Alta Badia
    (Rossato 2025).
11. **Nunatak inventory.** The specific Dolomite peaks that stood above the
    ~2 000 m thick LGM ice (e.g. Marmolada 3 343 m, Antelao 3 264 m, Tofana
    di Mezzo 3 244 m, Cristallo 3 221 m, Sassolungo 3 181 m, Cima di
    Lavaredo 2 999 m) were not sourced from a published nunatak-mapping
    paper in this pass. A dedicated Dolomite trimline / nunatak paper
    exists (search hits mention Guerreschi, Baroni, or Ivy-Ochs sub-topics
    but I did not verify one specifically).
12. **P-Tr GSSP correlation package for Tesero/Bulla** — the Sr-isotope work
    (Chemical Geology 2022) and palynology (Cirilli et al. 2015) exist but
    the boundary carbon-isotope curve dataset itself was not sourced to a
    specific repository here.

---

## Honesty labels

Suggested per-class UI labelling scheme so the site never over-claims:

| UI label | Meaning | Applies to |
|---|---|---|
| **observed** | Direct measurement of a modern quantity, or a physical count on a preserved specimen/section. | RGI 7.0 outlines; Sánchez 2018 GNSS velocities; Securo 2025 glacier area/volume; radiometric U-Pb ages on Triassic tuffs (e.g. Bagolino 241 Ma); Prati di Stuores stratigraphy. |
| **dated** (a sub-class of observed) | Age model derived from a chronometer with quoted uncertainty. | 10Be / 36Cl exposure ages (Rossato 2025 Alta Badia, Ivy-Ochs 2013 Lavini di Marco); 14C on foreland moraines; astronomical tuning in CENOGRID. |
| **interpreted** | A field/stratigraphic reconstruction that combines observations with expert judgment (mapping, correlation, biozonation, moraine attribution). | LGM extent maps (GLACIMONTIS, Ehlers/Gibbard, Bini 2009); LIA outlines pre-photography; nunatak lists; landslide source-area reconstructions; GSSP correlations from Meishan to Tesero. |
| **modeled** | Output of a numerical simulation or statistical model (fit, LOESS, data assimilation, ice-sheet model). | Seguinot 2018 ice thickness/velocity fields; Reinthaler & Paul 2025 LIA ice-thickness grids; Werner 2026 resolution study; PhanDA GMST/CO2 percentiles; Foster 2017 CO2 LOESS; Miller 2020 sea-level (backstripping + geochemical inversion — call it *modeled*). |
| **compiled** | A harmonized multi-source database (proxy compilations, meta-analyses). | CenCO2PIP; PhanSST; RGI (compilation of national inventories). |
| **artistic** | A rendering or illustration produced for the site with no primary source, or an inferred paleogeographic sketch. | Any hand-drawn Tethys sea illustration; any Dolomite reef "reconstruction art"; any color-graded cross-section beyond what the source paper shows. |

The bar to clear: any pixel driven by a number goes into observed / dated /
interpreted / modeled / compiled with its citation; anything else is *artistic*.

---

## Recommended datasets for a first prototype

For a single first prototype, use these six datasets — they are open,
verifiable, and cover the strongest storytelling beats:

1. **Deep-time temperature backbone (485 Ma → 0):**
   Judd et al. 2024 PhanDA — `PhanDA_GMSTandCO2_percentiles.csv` from
   https://github.com/EJJudd/PhanDA . CC-BY-4.0. One CSV, 85 rows, plottable
   directly. Provides both GMST and CO2 with credible intervals — label
   **modeled**.

2. **High-resolution Cenozoic climate (66 Ma → 0):**
   Westerhold et al. 2020 CENOGRID from PANGAEA
   (https://doi.pangaea.de/10.1594/PANGAEA.917503). 2-5 kyr resolution
   benthic δ¹⁸O/δ¹³C. Anchors the Cenozoic tab; useful for the Icehouse
   transition. Label **observed** (isotopic) + **dated** (astronomical age
   model).

3. **Pleistocene sea-level (800 ka → 0):**
   Spratt & Lisiecki 2016 stack, NOAA text file
   (https://www.ncei.noaa.gov/pub/data/paleo/contributions_by_author/spratt2016/).
   Label **modeled** (PC1 of 7 records with CI).

4. **LGM ice extent — Dolomites-relevant:**
   Start with the GLACIMONTIS 2026 open geodatabase; back-stop with Reinthaler
   & Paul 2025 for the modern-baseline LIA outlines (Zenodo 14336826), which
   explicitly includes the Dolomites region. Both CC-BY-4.0. Labels
   **compiled** / **interpreted**.

5. **Alpine ice-sheet animation over the last glacial cycle:**
   Seguinot et al. 2018 Zenodo continuous variables
   (https://zenodo.org/record/1423176). Pull one 1 km NetCDF (e.g. the EPICA
   forcing, palaeo-precip variant), extract ice thickness at 1 kyr, animate
   as a scroll-linked map layer. Label **modeled**. Cover the Dolomites
   with a mask from GLACIMONTIS.

6. **Present-day glacier baseline:**
   RGI 7.0 region 11 (Central Europe) polygons for the "today" state
   (NSIDC DOI 10.5067/F6JMOVY5NAVZ). Label **observed**.

**Two more to reach for as soon as feasible:**

- Judd et al. 2024 CO2 percentiles (already inside the same CSV as GMST) —
  becomes the CO2 curve without touching the CenCO2PIP compilation.
- Sánchez et al. 2018 vertical velocity field
  (https://doi.pangaea.de/10.1594/PANGAEA.886889) — turns "the Dolomites are
  still rising" into a labelled number (~1-1.5 mm/yr in the southern Eastern
  Alps).

**Do NOT ship in the first prototype without an extra verification pass:**

- Haq sea-level curves — absolute amplitudes are known-controversial; if used,
  label **interpreted** and cite the criticisms.
- Ehlers/Gibbard shapefiles — licensing likely restricts open web
  redistribution. GLACIMONTIS 2026 is the open replacement.
- Any paleogeographic map behind the Dolomites reef panorama — those are
  paintings; label **artistic** unless a specific vetted paleogeography (e.g.
  Scotese PALEOMAP with a rights statement) is licensed for reuse.
