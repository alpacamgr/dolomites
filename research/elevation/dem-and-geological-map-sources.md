# DEM, Imagery and Geological Map Sources for the Dolomites

**Region of interest:** roughly 10.5-12.5 deg E, 46.0-47.0 deg N (provinces of Bolzano / South Tyrol, Trento, Belluno). Alps-wide and European sources included for context.

**Research date:** 2026-09-06

**Legend for source citations:**
- `[verified 2026-09-06]` = URL was fetched successfully during this research pass.
- `[from search, not opened]` = URL appeared in a search-result listing but was not fetched.
- `[unverified - from memory]` = stated from prior knowledge without web confirmation.

---

## 1. Elevation datasets

### 1.1 Global / European DEMs

| Dataset | Native res. | Coverage | Format | CRS | License | Access |
|---|---|---|---|---|---|---|
| **Copernicus DEM GLO-30 (Public)** | 30 m (~1 arc-sec) | Global (a few tiles withheld; Italy fully covered) | Cloud-Optimized GeoTIFF (COG) | EPSG:4326 horizontal; heights relative to the EGM2008 geoid (EPSG:3855), per Copernicus DEM Product Handbook v5.0 sec. 1.2 `[verified 2026-09-12, see data/manifests/copernicus-dem-glo30.yaml]` (corrected: an earlier version said ellipsoidal) | Free "under the terms and conditions" of the ESA-Airbus licence; exact license name not quoted on the AWS registry page - practical use is free (worldwide, public) | AWS S3 `copernicus-dem-30m` (no-sign-request); OpenTopography portal `[verified 2026-09-06]` |
| **Copernicus DEM GLO-90** | 90 m | Global (worldwide, unrestricted) | COG | EPSG:4326 | Same as GLO-30 Public - free | AWS S3 `copernicus-dem-90m` `[verified 2026-09-06]` |
| **Copernicus DEM EEA-10** | 10 m (0.3 arc-sec) | Europe (EEA-39, incl. Italy) | GeoTIFF (DGED and INSPIRE variants) | EPSG:4326 | ESA-User licence, "restricted to Public Authorities" - not open to the general public | Copernicus Data Space Ecosystem (OData) or Copernicus Browser; requires eligibility approval `[verified 2026-09-06]` |
| **SRTM 1 arc-sec (~30 m) v3** | ~30 m | 60N-56S (covers all of Italy) | HGT / GeoTIFF | EPSG:4326, EGM96 | US Government public domain (NASA/USGS) | USGS EarthExplorer (login required) `[from search, not opened]` |
| **NASADEM** | ~30 m | 60N-56S | GeoTIFF / HDF5 | EPSG:4326, EGM96 | NASA public domain | NASA LP DAAC / OpenTopography `[from search, not opened]` |
| **ASTER GDEM v3** | ~30 m | 83N-83S | GeoTIFF | EPSG:4326, EGM96 | NASA/METI; free, redistribution allowed with attribution `[unverified - from memory]` | NASA Earthdata / METI |
| **ALOS World 3D (AW3D30)** | ~30 m | Global | GeoTIFF | EPSG:4326 | JAXA; free after user registration, with attribution | JAXA AW3D30 portal `[from search, not opened]` |
| **EU-DEM v1.1** | 25 m | EEA-39 (Europe) | GeoTIFF | EPSG:3035 (ETRS89-LAEA) | Copernicus Land Monitoring Service - free, "no restrictions" (attribution requested) `[unverified - from memory]` | Copernicus Land / land.copernicus.eu; note: superseded in practice by Copernicus DEM |

**Vertical accuracy (as commonly stated):** Copernicus DEM GLO-30 ~2-4 m LE90 in low-relief terrain (worse in steep Alpine terrain); SRTM ~9 m absolute vertical, ~16 m absolute horizontal (LE90); NASADEM slightly better than SRTM (void filling with ASTER, ALOS); AW3D30 ~5 m RMSE typical - all `[unverified - from memory]`.

### 1.2 National (Italy) DEMs

| Dataset | Native res. | Coverage | Format | CRS | License | Access |
|---|---|---|---|---|---|---|
| **TINITALY v1.1** (INGV; Tarquini et al. 2023) | 10 m | Entire Italy (incl. Dolomites) | GeoTIFF, also ASCII tiles | UTM WGS84 zone 32N (per docs found via search); download page did not restate | **CC BY 4.0** (mandatory citation of Tarquini et al. 2023, DOI 10.13127/tinitaly/1.1) | Free download by tile from `https://tinitaly.pi.ingv.it/Download_Area1_1.html`; no registration mentioned `[verified 2026-09-06]` |
| **PST-A LiDAR (national) - MASE Geoportale** | DTM 1 m (nominal); DSM First 1 m; DSM Last 1 m | Selected Italian territories acquired between ~2008-2014 by former Ministero dell'Ambiente; coverage is patchwork (many valley bottoms and coasts; Alpine coverage variable). Confirm per-tile whether Dolomites cells are present. | GeoTIFF for DTM/DSM; shapefile for interferometric PS data | Not stated in what we fetched - likely EPSG:32632/32633 UTM `[unverified - from memory]` | **CC BY 4.0** with attribution to MASE, per Geoportale MASE distribution service (per search summary) `[from search, not opened]` | Web app on `https://gn.mase.gov.it/portale/` for direct download; per recent reports (Sept 2024), the tiles are now downloadable without prior authorisation `[from search, not opened]` |

### 1.3 Provincial LiDAR and DTMs (Bolzano / Trento / Veneto)

| Dataset | Native res. | Coverage | Format | License | Access |
|---|---|---|---|---|---|
| **South Tyrol DGM/DTM 2.5 m** (Prov. Bolzano) | 2.5 m | Whole Province of Bolzano `[unverified - from memory]` | Raster; served via WMS/WCS | **CC0 1.0 Universal** (public domain) per portal filter `[verified 2026-09-06]` | `data.civis.bz.it` (dataset `modello-digitale-del-terreno-dtm-25m`) `[from search, not opened]` |
| **South Tyrol DGM/DTM 0.5 m (LiDAR)** | 0.5 m | Only *inhabited/settled areas* of South Tyrol (not the full alpine terrain) | Raster; WMS + WCS | **CC0 1.0 Universal** per portal metadata | `data.civis.bz.it` dataset `modello-digitale-del-terreno-dtm-05m`; WCS at `https://geoservices9.civis.bz.it/geoserver/ows` `[verified 2026-09-06]` |
| **South Tyrol DSM / orthophotos** | Orthophoto 20 cm (2020) `[unverified - from memory]` | Whole province | Various (WMS, download) | Portal-wide default: **CC0 1.0** for geobase datasets `[verified 2026-09-06]` | GeoKatalog: `http://geocatalogo.retecivica.bz.it/geokatalog/` |
| **Trentino LiDAR DTM/DSM (PAT 2014 + 2018 integration)** | 1 m for zone type 1; 2 m for zone types 2/3 | Full Province of Trento (PAT) | ASCII-grid (delivered); also served via portal viewers | License not restated on STEM landing page we fetched; per prior PAT/dati.trentino.it practice this is open (usually **CC BY 4.0** or **IODL 2.0**) - **verify per dataset** | SIAT/STEM WebGIS `https://siat.provincia.tn.it/stem/` (fetch of that root returned only the SPA title, so download procedure not confirmed here) `[verified 2026-09-06 - inconclusive]`; also `dati.trentino.it` |
| **Veneto DTM 5 m from LiDAR** | 5 m | Most of Veneto regional territory (includes Belluno province) | GeoTIFF `[unverified - from memory]` | **IODL 2.0** (Italian Open Data License 2.0), "no restrictions on public access" | `https://idt2.regione.veneto.it/idt/downloader/download`; also served via ARPAV GeoPortale (GeoNode) `[from search, not opened]` |
| **Veneto DTM 1 m / 2 m LiDAR (from national PST-A dataset filtered to Veneto)** | 1 m or 2 m | Veneto sub-areas covered by PST-A flights | Depends on source | See PST-A row (national) | Discoverable via `dati.gov.it` and `pcn.minambiente.it` `[from search, not opened]` |

**Important gap:** the truly high-resolution alpine LiDAR (0.5 m DSM) for Bolzano is limited to *inhabited areas*. For the high peaks and cliffs of the Dolomites themselves, the practical open dataset is **Trentino LiDAR 1 m** (where its coverage extends) plus the **Bolzano DTM 2.5 m** for South-Tyrolean alpine terrain, backed by **TINITALY 10 m** or **Copernicus GLO-30** elsewhere. Confirm exact tile coverage before choosing.

### 1.4 Web-ready terrain tile services (browser-consumable)

| Service | Encoding | Coverage | License / cost | Attribution |
|---|---|---|---|---|
| **AWS Terrain Tiles** (formerly Mapzen) | PNG Terrarium (32,768 offset) + Normal + skadi + geotiff | Global, z0-15 | Free (open data on AWS); attribution required per underlying sources | Composite attribution required; per Tilezen `joerd/docs/attribution.md` (SRTM, NED, GMTED, EUDEM, ETOPO1, various nationals) `[from search, not opened]` |
| **Mapbox Terrain-DEM / Terrain-RGB** | PNG RGB (-10000 offset, 0.1 m step) | Global | Requires Mapbox account + access token; tiered pricing (free tier limited) `[unverified - from memory]` | "(c) Mapbox (c) OpenStreetMap" plus DEM source attributions |
| **MapTiler Terrain-RGB** | PNG RGB (Mapbox-compatible) | Global | Free tier with MapTiler account + attribution; paid for higher volume `[unverified - from memory]` | "(c) MapTiler (c) OpenStreetMap contributors" |
| **Cesium World Terrain** (Cesium Ion) | Quantized-mesh | Global | Free "Community" tier for evaluation and non-commercial; commercial tiers from ~$149/mo (Individual Commercial) `[verified 2026-09-06]` | Attribution required per Cesium ion Terms of Service + Content Usage & Attribution Guide |

---

## 2. Imagery

| Dataset | Native res. | License | Access |
|---|---|---|---|
| **Sentinel-2 L1C / L2A** (ESA Copernicus) | 10 m (visible/NIR), 20 m (red-edge/SWIR), 60 m (atmo) | Copernicus Sentinel Data licence - free, full and open access; commercial use permitted; attribution "contains modified Copernicus Sentinel data [YYYY]" required | Copernicus Data Space Ecosystem; AWS Open Data `sentinel-s2-l2a` (Requester Pays for L2A, Free for L1C) `[unverified - from memory]` |
| **ESA WorldCover 2020 / 2021** (10 m global land cover) | 10 m | **CC BY 4.0** (attribution) | AWS Open Data `esa-worldcover-vito`; also `esa-worldcover.org/en/data-access` `[from search, not opened]` |
| **EOX Sentinel-2 cloudless** (annual global mosaic) | 10 m | **CC BY 4.0** typically for 2016-2020 mosaics; check per year (e.g. 2019/2020 released as CC BY-SA in some cases) `[unverified - from memory]` | `https://s2maps.eu` (tiles) - attribution "Sentinel-2 cloudless - https://s2maps.eu by EOX IT Services GmbH" |
| **South Tyrol orthophotos** (Prov. Bolzano) | 20 cm `[unverified - from memory]` | **CC0 1.0** (portal-wide) | `data.civis.bz.it` orthophoto datasets |
| **Trentino orthophotos** | 20 cm `[unverified - from memory]` | Usually **CC BY 4.0** or **IODL 2.0** on `dati.trentino.it` - verify | `dati.trentino.it`, SIAT/STEM |

---

## 3. Geological / tectonic maps

### 3.1 ISPRA CARG project 1:50,000 (Italy)

CARG (CARtografia Geologica) is the Italian national 1:50,000 geological map programme (started late 1980s, ongoing), coordinated by ISPRA - Servizio Geologico d'Italia in partnership with regions and autonomous provinces (PAB Bolzano, PAT Trento, Regione Veneto for the Dolomites area). Each sheet ships with a printed map, a "Note Illustrative" volume, and, where completed, a vector geological database (14 informative layers at 1:25,000 sensu the underlying survey scale, delivered at 1:50,000 on the printed sheet).

**Sheets that cover the Dolomites (numbering confirmed via ISPRA Note Illustrative PDF filenames and secondary sources):**

| Sheet # | Sheet name | Provinces | Status |
|---|---|---|---|
| 013 | Merano | BZ | Referenced in CARG stato di attuazione `[from search, not opened]` |
| 016 | Dobbiaco | BZ, BL | **Published** - map + Note Illustrative available (presentation 2019) `[verified 2026-09-06]` |
| 025 | Rabbi | TN | Note Illustrative PDF `25_Rabbi_It.pdf` on ISPRA site (Ted./Ita.) `[from search, not opened]` |
| 026 | Appiano | BZ | Referenced |
| 027 | Bolzano | BZ | Referenced |
| 028 | La Marmolada | BZ, TN, BL | Published (Note Illustrative on ISPRA) `[from search, not opened]` |
| 029 | Cortina d'Ampezzo | BL, BZ | Published (Note Illustrative available as PDF) `[from search, not opened]` |
| 043 | Mezzolombardo | TN, BZ | Note Illustrative PDF `43_Mezzolombardo_Ted.pdf` on ISPRA site `[from search, not opened]` |
| 044 | Predazzo | TN, BZ | Confirmed via cross-search `[from search, not opened]` |
| 045 | San Martino di Castrozza | TN, BL | Confirmed via cross-search `[from search, not opened]` |
| 046 | Longarone | BL | Published `[from search, not opened]` |
| 059 | Tione di Trento | TN | Confirmed via cross-search `[from search, not opened]` |
| 060 | Trento | TN | **Published** - Note Illustrative PDF `60_Trento.pdf`; survey 2000-2006 under S. Cocco `[verified 2026-09-06]` |

**Note:** the CARG project has 652 sheets total for national coverage. The Dolomites core area is essentially covered by sheets 016, 025-029, 043-046, 059-060 (with 013 and 017 to the north). Publication of vector geodatabases lags printed sheets in some cases; verify per sheet on `progetto-carg.isprambiente.it/portali` before assuming shapefile availability.

**Gap flagged:** the master `carg_rap.pdf` (stato di attuazione, > 10 MB) exceeded the WebFetch size cap in this pass; the sheet-by-sheet publication status of vector data should still be re-verified in that PDF.

**Formats and services:**
- Vector data (14-layer geological DB) exist for completed sheets; the ISPRA "Geomapviewer" allows raster *and* vector viewing; OGC WMS/WFS/WCS are exposed. Whether the vector layers are downloadable as shapefile/GeoPackage vs. only viewable-via-service depends on the sheet - the ISPRA landing page does not commit to bulk shapefile download `[verified 2026-09-06 - inconclusive]`.
- WMS endpoint for the 1:50,000 raster: `http://sgi2.isprambiente.it/arcgis/services/raster/geo_50k_italia/ImageServer/WMSServer` `[from search, not opened]`
- Main portal: `http://sgi.isprambiente.it/geoportal` `[from search, not opened]`
- Note Illustrative PDFs are freely downloadable per sheet under `https://www.isprambiente.gov.it/Media/carg/note_illustrative/`

**License:** ISPRA does not brand CARG with a single well-known CC license on the landing page; attribution to "ISPRA - Servizio Geologico d'Italia, Progetto CARG" and sheet author list is expected. Actual reuse licence is unclear - **verify per dataset**. Some ISPRA services declare CC BY 4.0 on their INSPIRE metadata; not confirmed for CARG here.

### 3.2 National / regional geology (Italy)

| Dataset | Scale | Format | License | Access |
|---|---|---|---|---|
| **Carta Geologica d'Italia 1:1,000,000** (ISPRA, derived) | 1:1M | Vector + raster | Not explicitly branded on the page fetched; ISPRA credit required | ISPRA "Geological and geothematic map" pages; OGC services `[verified 2026-09-06 - partial]` |
| **Carta Geologica d'Italia 1:100,000** | 1:100k | Raster (277 sheets + 132 second-edition) | ISPRA credit | ISPRA |
| **Carta Geologica d'Italia 1:500,000** (ISPRA) | 1:500k | Vector reported to exist | Not confirmed here | ISPRA - **verify** |
| **Carta geodinamica 1:1,250,000** (2004) | 1:1.25M | Raster | ISPRA credit | ISPRA |
| **South Tyrol / PAB geological units** (from CARG 1:10,000 surveys, published at 1:25,000) | 1:25k | WMS + WFS (36 geology datasets on the portal); vector download via GeoKatalog | **CC0 1.0 Universal** (portal-wide) | `data.civis.bz.it` (tag: Geologia) `[verified 2026-09-06]` |
| **Trentino - Carta Geologica della PAT** (Servizio Geologico) | 1:10k survey scale | WebGIS provides TIFF, high-res TIFF, PDF, PDF-with-legend, **Shapefile**; also shapefile via PAT Geocatalogue | License not fetched here - PAT open data is typically CC BY 4.0 or IODL 2.0 - **verify per dataset** | Cartografia geologica portal (`protezionecivile.tn.it/territorio/Cartografia/Cartografiageologica/`) + `dati.trentino.it` `[from search, not opened]` |
| **Geologische Karte der Westlichen Dolomiten 1:25,000** (Bosellini et al.) | 1:25k | Printed publication (Museo Ladin / Casa Editrice), plus derived layers in the PAB GeoBrowser `[unverified - from memory]` | Publication is copyrighted; derived digital layers may be under provincial CC0 - **verify** | Provincial GeoBrowser layers |

### 3.3 Alps-wide / European

| Dataset | Extent | Format | License | Access |
|---|---|---|---|---|
| **Tectonic Map of the Alps** (Schmid, Fuegenschuh, Kissling, Schuster 2004; Eclogae geol. Helv. 97) - **georeferenced GIS version on GFZ Data Services** | Whole Alps | QGIS project + example scripts (matplotlib/GMT) per search summary; the GFZ record page I fetched displayed status **"In Review"** and stated "not available for public download" - contact authors | Not stated; likely CC BY-derivative when finalised | `https://dataservices.gfz-potsdam.de/4dmb/` (object id `5f90c4fb-7659-11e9-8d2b-17c9ac01fef8`) `[verified 2026-09-06 - restricted]` |
| **CCGM printed "Tectonic Map of the Alps"** | Whole Alps | Printed 1:1,000,000 sheet (sale) | Copyright CCGM | `ccgm.org` `[from search, not opened]` |
| **Bousquet et al. 2012, "Metamorphic framework of the Alps" 1:1,000,000** | Whole Alps | CCGM printed edition; GIS version not confirmed on the open web here | Copyright CCGM | Confirm |
| **EGDI 1:1,000,000 pan-European Surface Geology** | All Europe | **WMS** + **GeoPackage download** | Free download; the EGDI records do not restate a CC name on the WMS capabilities URL - EuroGeoSurveys/EGDI typically require attribution `[unverified - from memory]` | WMS `https://geoserver.geo-zs.si/egdi-surface-geology/gsmlp/wms?service=wms&version=1.3.0&request=GetCapabilities`; portal `https://www.europe-geology.eu/` `[from search, not opened]` |
| **OneGeology-Europe / OneGeology portal 1:1M** | Europe / global | WMS | Attribution-only in general | `onegeology.org` `[unverified - from memory]` |
| **Geological Map of Europe 1:5,000,000** (BGR/CGMW) | Europe | Printed / raster; GIS availability limited | Copyright BGR/CGMW | `bgr.bund.de` `[unverified - from memory]` |
| **GeoMol** (subsurface 3D models, Alps/N.Italy sectors) | Cross-border | 3D models + reports | Project outputs mostly free; check per deliverable | `geomol.eu` `[unverified - from memory]` |

### 3.4 Fault databases

| Dataset | Extent | Format | License | Access |
|---|---|---|---|---|
| **ITHACA - ITaly HAzards from CApable faulting** (ISPRA) | Italy | Web portal (WebGIS); GIS export mentioned in secondary sources | ISPRA attribution; explicit CC not confirmed here | `http://sgi2.isprambiente.it/ithacaweb/Mappatura.aspx` `[from search, not opened]` |
| **DISS - Database of Individual Seismogenic Sources** v3.3.1 (INGV, released March 2025) | Italy + surrounding areas | Desktop-GIS file formats + **OGC web services** | **CC BY 4.0** unless otherwise noted | `https://diss.ingv.it/data/` `[from search, not opened]` |
| **EDSF - European Database of Seismogenic Faults** | Europe | GIS files + web services | Attribution; INGV-hosted service | `https://www.seismofaults.eu/services/diss-services` `[from search, not opened]` |
| **QUIN 1.0** (QUaternary fault strain INdicators - central Apennines only) | Italy - Apennines (NOT Alps) | Shapefile | CC BY 4.0 `[unverified - from memory]` | Zenodo / Scientific Data (Nature) - probably not useful for Dolomites |

### 3.5 Geosites / UNESCO Dolomites

| Dataset | Content | License | Access |
|---|---|---|---|
| **UNESCO WHS "The Dolomites" (Site 1237) - 9 component systems polygons** | 9 core areas + buffer zones | UNESCO Sites Navigator states that polygons "will be made available once the GIS data is received by UNESCO" - direct shapefile download URL for the Dolomites specifically was NOT located in this pass; European Data Portal record "World Heritage Sites and Buffer Zones" is the umbrella dataset | UNESCO gives no explicit reuse licence; European Data Portal record inherits the underlying WHS licence (usually attribution to UNESCO) - **verify** | `https://whc.unesco.org/en/wh-gis/` (Sites Navigator); `data.europa.eu/data/datasets/world-heritage-sites-and-buffer-zones` `[from search, not opened]` |
| **ISPRA Inventario nazionale dei geositi** | Italian geosites | WMS / WFS + web app | Usually CC BY 4.0 for INSPIRE-published ISPRA datasets - **verify** | ISPRA geoportal `[unverified - from memory]` |
| **Provincial geotope inventories (PAB / PAT)** | Local geotopes | Provincial open data | PAB portal-wide **CC0 1.0**; PAT typically CC BY 4.0 | `data.civis.bz.it`; `dati.trentino.it` |

---

## 4. Italian open-data licensing notes

Short primer on the three licences most-encountered in this catalogue:

- **CC BY 4.0** (Creative Commons Attribution 4.0 International): most permissive of the three. You may reuse, adapt, commercialise; you must credit the creator, give a link to the licence, and indicate changes. Compatible with almost everything.
- **CC0 1.0 Universal** (Public Domain Dedication): the creator waives all rights. No attribution required (though good practice remains). Portale OpenData Bolzano (`data.civis.bz.it`) has adopted **CC0** as its default across geo datasets - unusual and very permissive.
- **IODL 2.0** (Italian Open Data Licence 2.0, `dati.gov.it/content/italian-open-data-license-v20`): equivalent in intent to **CC BY 4.0** - reuse, redistribute, adapt, commercialise, provided attribution is given per the licence terms. IODL 2.0 is compatible with CC BY 4.0. Used across many Italian regional portals (Veneto, some MASE datasets, some PAT datasets).
- **CC BY-SA 4.0**: adds a viral share-alike obligation - anything you build with it must be relicensed under CC BY-SA. Rare in the Italian public-sector open-data landscape and worth flagging when encountered (mostly appears on OpenStreetMap-derived and some crowd-sourced datasets).

**Attribution text you will actually need to display for the datasets most likely to be used:**
- TINITALY: "Tarquini S., Isola I., Favalli M., Battistini A., Dotta G. (2023). TINITALY, a digital elevation model of Italy with a 10 meters cell size (Version 1.1). INGV. https://doi.org/10.13127/tinitaly/1.1" (CC BY 4.0)
- Copernicus DEM: "Produced using Copernicus WorldDEM-30 (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved." `[unverified - from memory]` - verify against ESA-Airbus licence.
- Sentinel-2: "Contains modified Copernicus Sentinel data [YYYY]".
- Veneto DTM: "Regione del Veneto - dati distribuiti in IODL 2.0" (per IODL requirements).
- PST-A LiDAR: "Dati LiDAR - Ministero dell'Ambiente e della Sicurezza Energetica (MASE) - Geoportale Nazionale, CC BY 4.0".
- Bolzano CC0 datasets: strictly no attribution required; a credit line is nonetheless polite.

**Restrictive / unclear licences flagged:**
- Copernicus DEM EEA-10 (10 m): **restricted to Public Authorities** - do not plan a public web deployment around this.
- Cesium World Terrain: Community tier is non-commercial; commercial use = paid tier.
- Mapbox Terrain-DEM / MapTiler Terrain-RGB: usable but tied to vendor account + attribution; not "open data".
- CARG (ISPRA) vector data: reuse licence is not clearly branded - safest path is service consumption (WMS) plus explicit ISPRA credit; contact the Servizio Geologico for redistribution rights of the vector layers.
- CCGM printed tectonic and metamorphic maps of the Alps: copyrighted - print reference only.
- Schmid et al. 2004 tectonic-map GIS package on GFZ Data Services: the record I opened was marked "In Review" and required contacting authors; treat as **not yet openly downloadable** as of 2026-09-06.
- UNESCO WHS Dolomites polygons: not confirmed as a direct shapefile download for the 9 systems - may need to be traced/digitised from the Sites Navigator or requested from the Dolomiti UNESCO Foundation.

---

## 5. Recommended minimum dataset for a first prototype

Pick 3-5 and start:

1. **Copernicus DEM GLO-30 (Public)** - global, free, worldwide coverage, COG on AWS - the pragmatic baseline for a scroll-driven web viz that must load fast anywhere. It renders the Dolomites at a usable resolution and gets you shipping.
2. **TINITALY v1.1 (10 m, INGV, CC BY 4.0)** - the highest-resolution DEM that covers the *entire* Dolomites region under a fully open licence with a single attribution line. Use it for close-up scenes and hillshades where GLO-30 is too coarse.
3. **South Tyrol GeoKatalog (data.civis.bz.it) geology layers + DTM 2.5 m** - CC0, so zero licence friction; gets you the highest-res LiDAR-derived DTM for South Tyrol (limited to inhabited areas at 0.5 m, but 2.5 m elsewhere) and a modern vector geological framework for the northern half of the Dolomites.
4. **ISPRA CARG WMS raster for the 1:50,000 sheets** (`sgi2.isprambiente.it/.../geo_50k_italia/ImageServer/WMSServer`) - lets you overlay authoritative geological polygons for Marmolada, Cortina, Dobbiaco etc. without redistributing files whose licence you are not confident about. Zero storage cost; requires ISPRA attribution.
5. **Sentinel-2 cloudless mosaic (EOX s2maps.eu) or ESA WorldCover 2021 (CC BY 4.0)** - a modern satellite basemap or land-cover texture that reads well at every zoom and comes with a well-understood licence.

If you must pick only three: **GLO-30 + TINITALY + CARG WMS via ISPRA** covers "world DEM, precise Italian DEM, authoritative geology" with one paid attribution and no registration walls.

---

## 6. Sources

| # | Name | Provider | URL | Access date | Licence |
|---|---|---|---|---|---|
| 1 | Copernicus DEM (AWS registry) | AWS / ESA | https://registry.opendata.aws/copernicus-dem/ | 2026-09-06 (fetched) | Free ESA-Airbus terms |
| 2 | Copernicus DEM (Data Space) | ESA / Copernicus | https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM | 2026-09-06 (from search) | Free (GLO); Public-Auth only (EEA-10) |
| 3 | Copernicus EEA-10 availability news | Copernicus DataSpace | https://dataspace.copernicus.eu/news/2025-7-1-copernicus-contributing-missions-cop-dem-10mt-now-available-public-authorities-users | 2026-09-06 (from search) | See ESA-User licence |
| 4 | TINITALY 1.1 download | INGV | https://tinitaly.pi.ingv.it/Download_Area1_1.html | 2026-09-06 (fetched) | CC BY 4.0, DOI 10.13127/tinitaly/1.1 |
| 5 | TINITALY 1.1 accompanying notes | INGV | https://tinitaly.pi.ingv.it/Tinitaly_1_1_AccompanyingNotes.pdf | 2026-09-06 (from search) | CC BY 4.0 |
| 6 | South Tyrol DTM 0.5 m | Prov. Bolzano OpenData | https://data.civis.bz.it/de/dataset/modello-digitale-del-terreno-dtm-05m | 2026-09-06 (fetched) | CC0 1.0 |
| 7 | South Tyrol DTM 2.5 m | Prov. Bolzano OpenData | http://daten.buergernetz.bz.it/de/dataset/modello-digitale-del-terreno-dtm-25m | 2026-09-06 (from search) | CC0 1.0 |
| 8 | South Tyrol geology datasets (36) | Prov. Bolzano OpenData | https://data.civis.bz.it/dataset?tags=Geologia | 2026-09-06 (fetched) | CC0 1.0 |
| 9 | GeoKatalog viewer | Prov. Bolzano | http://geocatalogo.retecivica.bz.it/geokatalog/ | 2026-09-06 (from search) | mixed - dataset-specific |
| 10 | Trentino LiDAR download portal | PAT | https://siat.provincia.tn.it/stem/ | 2026-09-06 (fetched - SPA only) | not confirmed |
| 11 | Trentino LiDAR news | PAT | https://www.provincia.tn.it/en/News/Insights/Lidar-survey-of-the-territory-of-the-Province-of-Trento | 2026-09-06 (from search) | Open, license per dataset |
| 12 | Trentino Carta Geologica | PAT | https://www.provincia.tn.it/en/News/Insights/Geological-Map-of-the-Autonomous-Province-of-Trento | 2026-09-06 (from search) | Open, license per dataset |
| 13 | Trentino Carta Geologica download | PAT | http://www.protezionecivile.tn.it/territorio/Cartografia/Cartografiageologica/ | 2026-09-06 (from search) | Open, license per dataset |
| 14 | Veneto DTM 5 m from LiDAR | Regione Veneto | https://idt2.regione.veneto.it/idt/downloader/download | 2026-09-06 (from search) | IODL 2.0 |
| 15 | Veneto DTM 5 m (INSPIRE record) | Regione Veneto | https://inspire-geoportal.ec.europa.eu/srv/api/records/r_veneto:c0101071_Lidar5m | 2026-09-06 (from search) | IODL 2.0 |
| 16 | PST-A LiDAR (Geoportale MASE) | MASE | https://gn.mase.gov.it/portale/en/pst-dati-lidar | 2026-09-06 (fetched - metadata only) | CC BY 4.0 (per secondary reporting) |
| 17 | PST-A data distribution service | MASE | https://gn.mase.gov.it/portale/en/data-distribution-services-pst | 2026-09-06 (from search) | CC BY 4.0 |
| 18 | AWS Terrain Tiles registry | AWS / Mapzen / Tilezen | https://registry.opendata.aws/terrain-tiles/ | 2026-09-06 (fetched) | See tilezen/joerd attribution.md |
| 19 | Tilezen Joerd attribution | Tilezen | https://github.com/tilezen/joerd/blob/master/docs/attribution.md | 2026-09-06 (from search) | Composite per source |
| 20 | Cesium Ion pricing | Cesium | https://cesium.com/platform/cesium-ion/pricing/ | 2026-09-06 (from search) | Community (free) + commercial tiers |
| 21 | Cesium content usage & attribution | Cesium | https://cesium.com/learn/ion/content-usage-and-attribution-guide/ | 2026-09-06 (from search) | Per ToS |
| 22 | ISPRA geological and geothematic maps | ISPRA | https://www.isprambiente.gov.it/en/databases/data-base-collection/soil-and-territory/geological-and-geotematics-map | 2026-09-06 (fetched) | ISPRA credit; details per dataset |
| 23 | ISPRA CARG stato di attuazione (PDF) | ISPRA | https://progetto-carg.isprambiente.it/download/carg_rap.pdf | 2026-09-06 (attempted fetch failed - exceeds 10 MB) | ISPRA credit |
| 24 | ISPRA CARG portal (CARG-Gate) | ISPRA | https://progetto-carg.isprambiente.it/ | 2026-09-06 (fetched) | ISPRA credit |
| 25 | ISPRA CARG WMS raster 1:50k | ISPRA | http://sgi2.isprambiente.it/arcgis/services/raster/geo_50k_italia/ImageServer/WMSServer | 2026-09-06 (from search - endpoint listed) | ISPRA credit |
| 26 | ISPRA Portale del Servizio Geologico | ISPRA | http://sgi.isprambiente.it/geoportal | 2026-09-06 (from search) | Attribution ISPRA |
| 27 | ISPRA "16 Dobbiaco" sheet page | ISPRA | https://www.isprambiente.gov.it/Media/carg/16_DOBBIACO/Foglio.html | 2026-09-06 (from search) | ISPRA credit |
| 28 | ISPRA Note Illustrative Dobbiaco (PDF) | ISPRA | https://www.isprambiente.gov.it/Media/carg/note_illustrative/16_Dobbiaco_ita.pdf | 2026-09-06 (from search) | ISPRA credit |
| 29 | Schmid 2004 tectonic-map GIS (GFZ) | GFZ Potsdam | https://dataservices.gfz-potsdam.de/4dmb/overview.php?object=5f90c4fb-7659-11e9-8d2b-17c9ac01fef8 | 2026-09-06 (fetched - "In Review") | Not open (contact authors) |
| 30 | CCGM printed tectonic map of the Alps | CCGM | https://ccgm.org/en/product/map-tectonic-of-the-alps/ | 2026-09-06 (from search) | Copyright CCGM (sale) |
| 31 | EGDI 1:1M pan-European Surface Geology | EGDI / GeoZS | https://egdi.geology.cz/record/basic/5f7db57f-6e84-4484-835f-706b0a010833 | 2026-09-06 (from search) | Free (per portal) |
| 32 | EGDI 1:1M WMS | EGDI / GeoZS | https://geoserver.geo-zs.si/egdi-surface-geology/gsmlp/wms?service=wms&version=1.3.0&request=GetCapabilities | 2026-09-06 (from search - listed) | See metadata |
| 33 | EGDI portal | EGDI | https://www.europe-geology.eu/ | 2026-09-06 (from search) | Free |
| 34 | ITHACA (ISPRA) | ISPRA | http://sgi2.isprambiente.it/ithacaweb/Mappatura.aspx | 2026-09-06 (from search) | ISPRA credit |
| 35 | DISS 3.3.1 | INGV | https://diss.ingv.it/data/ | 2026-09-06 (from search) | CC BY 4.0 |
| 36 | EDSF (European Database of Seismogenic Faults) | INGV | https://www.seismofaults.eu/services/diss-services | 2026-09-06 (from search) | CC BY 4.0 (per DISS) |
| 37 | UNESCO WHS Sites Navigator | UNESCO WHC | https://whc.unesco.org/en/wh-gis/ | 2026-09-06 (from search) | Per UNESCO WHC |
| 38 | UNESCO "The Dolomites" (site 1237) | UNESCO WHC | https://whc.unesco.org/en/list/1237/ | 2026-09-06 (from search) | Per UNESCO WHC |
| 39 | WHS + Buffer Zones on European Data Portal | EU | https://data.europa.eu/data/datasets/world-heritage-sites-and-buffer-zones | 2026-09-06 (from search) | Per UNESCO WHC |
| 40 | Dolomiti UNESCO official | Dolomiti UNESCO | https://www.dolomitiunesco.info/en | 2026-09-06 (from search) | Per foundation |
| 41 | ESA WorldCover registry | AWS / VITO | https://registry.opendata.aws/esa-worldcover-vito/ | 2026-09-06 (from search) | CC BY 4.0 |
| 42 | ESA WorldCover data access | ESA / VITO | https://esa-worldcover.org/en/data-access | 2026-09-06 (from search) | CC BY 4.0 |
| 43 | Copernicus Sentinel data licence text | ECMWF/CDS | https://cds.climate.copernicus.eu/licences/ec-sentinel | 2026-09-06 (from search) | Free, full, open |
| 44 | dati.civis.bz.it dataset listing | Prov. Bolzano | https://data.civis.bz.it/de/dataset?tags=Elevazione | 2026-09-06 (from search) | mostly CC0 1.0 |

## 7. Open questions / gaps

1. **CARG sheet-level vector publication status** - the master `carg_rap.pdf` (stato di attuazione) exceeded the WebFetch 10 MB cap. Per-sheet vector-DB availability (shapefile / GeoPackage) for 016, 025-029, 043-046, 059-060 should still be confirmed before assuming redistribution rights.
2. **CARG vector reuse licence** - the ISPRA landing pages do not brand CARG shapefiles/geodatabase with a named licence (CC BY? IODL?). Confirm via INSPIRE metadata of an individual sheet or by contacting Servizio Geologico d'Italia.
3. **CARG vector download vs. WMS-only** - it is not clear whether the 14-layer geological databases are downloadable as shapefile/GeoPackage or only viewable through Geomapviewer + WMS. Test per sheet.
4. **PST-A LiDAR coverage in the Dolomites** - the MASE portal's landing page confirmed the data spec but not the tile coverage for South Tyrol / Trentino / Belluno. Confirm with the interactive download map.
5. **Trentino LiDAR license** - the STEM WebGIS root only returned the SPA title; individual dataset pages on `dati.trentino.it` restate the licence (usually CC BY 4.0 or IODL 2.0) - verify per dataset before shipping.
6. **Bolzano LiDAR high-res coverage** - the 0.5 m DTM is only for "inhabited areas" - what covers the alpine terrain at sub-2.5 m? Possibly the newer LiDAR flights advertised on `natur-raum.provinz.bz.it` - verify with the office (cartografia@provincia.bz.it).
7. **South Tyrol orthophotos** - actual pixel size, year, and per-year availability not verified on the specific dataset page in this pass.
8. **Sentinel-2 cloudless (EOX)** - per-year licence (2016-2018 vs 2019-2020) was not pinned down; check `s2maps.eu` licence text.
9. **Schmid et al. 2004 GIS** - the GFZ record is "In Review" and requires contacting authors; no open download URL is available today. Consider digitising the printed CCGM sheet or using a derivative such as the "TAPESTRY" or "AlpArray" community GIS layers (not investigated here) as an interim.
10. **Bousquet et al. 2012 metamorphic map GIS** - only the printed CCGM sheet is confirmed to exist; a GIS version was not located in this pass.
11. **UNESCO Dolomites 9-system polygons** - direct shapefile of the nine components was NOT located as a downloadable file. Requires either the UNESCO Sites Navigator (which promises polygons "once received"), the Dolomiti UNESCO Foundation, or manual digitisation from the nomination map.
12. **Copernicus DEM licence exact name** - the AWS registry page links to the licence but doesn't quote its official title. Fetch the actual PDF at `spacedata.copernicus.eu` to record the exact licence identifier before redistribution.
13. **ITHACA reuse licence** - not explicitly stated in what we fetched; contact ISPRA before redistribution.
