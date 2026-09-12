# Geology gap-fill sources for the merged Dolomites geology archive

Research note, 2026-09-12. Research only: nothing in `data/scripts/`, the app code or `app/public/data/` was changed.
Draft manifests were written to `data/manifests/` and raw files to `data/raw/` for the three recommended datasets.
Coverage numbers were computed with throw-away scripts in the session scratchpad (shapely/geopandas in the project venv),
against `app/public/data/terrain/geology-coverage.geojson`. Areas are in square degrees of lon/lat, which is not an
equal-area measure; use them as proportions only.

## 1. The gaps, measured

Terrain bbox 10.3-12.7 E, 45.8-47.2 N (3.36 deg2). Current coverage (bz-geology-carg + pat-geology-carta-geologica +
veneto-litologia-250k) leaves **1.5609 deg2** without geology. Split by territory (Italy outline = union of the ISPRA
1:500k map, Austria = union of the GeoSphere 1:1M map, Switzerland = the remainder; borders are therefore approximate):

| Gap part | deg2 | Where |
|---|---|---|
| Italy, inside the Province of Bolzano (outline = union of the 116 municipalities in `p_bz-Inspire:AU.AdministrativeUnit`) | 0.4481 | Bolzano-Brixen strip, Pustertal west, parts of Vinschgau and the north-west |
| Italy, outside South Tyrol | 0.3181 | 0.1416 at 10.30-10.63 E / 45.80-46.55 N and 0.0065 at 10.53-10.84 E / 45.80-45.84 N (Lombardy side); 0.1663 at 12.32-12.70 E / 45.80-46.54 N (east of the Veneto coverage; Friuli Venezia Giulia by position, not checked against a boundary file) |
| Austria | 0.7310 | Tyrol and East Tyrol north of the border |
| Switzerland | 0.0637 | 10.30-10.49 E / 46.53-47.00 N (Lower Engadine, Val Müstair, Samnaun) |

The two Italian pieces outside South Tyrol were not in the problem statement but are real gaps in the bbox.

Checks against the CARG "aggregated" layer: WFS hit counts in 600 m boxes at Bolzano (11.354 E 46.498 N), Brixen
(11.657 E 46.716 N), Bletterbach (11.42 E 46.36 N) and Bruneck (11.94 E 46.80 N) are 0 for both
`p_bz-GeologicalMap:GeologicalUnits-Detailed` and `GeologicalUnits-Aggregated`, and 1 for both at the Seiser Alm control
point. The aggregated layer has the same survey gaps. [verified 2026-09-12]

## 2. Recommendation

Add three sources, one per territory, below the existing three:

| Priority | Dataset id | Licence | Scale | Fills | Raw data |
|---|---|---|---|---|---|
| 1-3 | bz-geology-carg, pat-geology-carta-geologica, veneto-litologia-250k | (unchanged) | | | |
| 4 | `swisstopo-geocover` (4 sheets) | swisstopo OGD terms (free use, source attribution mandatory) | 1:25,000 | 99% of the Swiss gap | `data/raw/swisstopo-geocover/` |
| 5 | `ispra-geologia-100k-inspire` | CC BY 4.0 | 1:100,000 (much coarser than 1:25k) | 98% of the South Tyrol gap (Bolzano, Bletterbach 100%, Brixen, Bruneck), 97% of the other Italian gaps | `data/raw/ispra-geologia-100k-inspire/` |
| 6 | `geosphere-geologicunits-500k` | CC BY 4.0 | 1:500,000 (20x coarser than 1:25k) | 100% of the Austrian gap | `data/raw/geosphere-geologicunits-500k/` |

Why this order: the three new maps are almost disjoint (each covers its own country), so the order only decides border
slivers; finer scale wins there. Priority 1 of the task (South Tyrol around Bolzano, Bletterbach, Brixen) is filled by
the ISPRA 1:100,000 map. It is the only open vector source found at better than 1:300,000 for those areas.

Together the three close about 99% of the 1.5609 deg2 gap. What remains are slivers along sheet and national borders
(about 2% of the South Tyrol part).

Conditions before shipping (details in the manifests):

1. **ISPRA ages need a review, not just a lookup table.** In the bbox, 244 of 1 072 units carry a metamorphicProcess
   event, and the "age" is then the metamorphism (e.g. orthogneiss = Cenozoic, Fillade quarzifera di Bressanone =
   Pennsylvanian). There are also harmonisation errors in the unit join (e.g. "dolomia dello sciliar" described as
   "Norico. - Dolomia principale", age Ladinian; "oliviniti" described as phyllites). Proposed rule: use ages only for
   depositional, intrusive and effusive events; leave metamorphic-event ages null or label them. A reviewer with
   geological training should check the gap-area units.
2. **Legend honesty:** the coverage note in the meta file should state the three new scales. 1:100,000 and 1:500,000
   polygons must not be presented as detailed at z12-13 (data policy rule 6).
3. The swisstopo top/base semantics are inferred from data, not yet read in the data-model PDF.

Not recommended now but worth a later look: GeoSphere 1:50,000 (CC BY 4.0, 1.03 GB) would replace the 1:500,000 map on
37% of the Austrian gap. It also reaches about 9% into the South Tyrol gap along the Brenner/Pfitsch border, where its
scale beats ISPRA. Separately, the ISPRA 1:100,000 map is finer than the Veneto 1:250,000 lithology map and has ages
for classes that Veneto leaves null. Replacing Veneto in Belluno would change the agreed priority, so it is only
flagged here.

## 3. Findings table (all checked 2026-09-12)

| Candidate | Provider | Landing / metadata | Download (tested) | Format | Scale | Licence (source) | Age attribute -> ICS? | Features | Size | Gap coverage | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Carta Geologica d'Italia 1:100.000 - Dataset, INSPIRE GML "nord" | ISPRA - Servizio Geologico d'Italia | https://geodati.gov.it/resource/id/ispra_rm:Geologia100K_DT ; Atom https://sgi3.isprambiente.it/download/GE.atom.TOP.en.xml | https://sgi3.isprambiente.it/download/gml_zip/Carta_geologica_100k_INSPIRE-GE_nord.zip (HTTP 200) | GML 3.2 INSPIRE ge-core 4.0, zipped | 1:100,000 (surveys 1880-1980) | CC BY 4.0 (RNDT record; Atom rights) | GeologicEvent olderNamedAge/youngerNamedAge = ICS chart URIs, 67 names in bbox; yes, with rules for Present/Precambrian/eras and metamorphic events | 3 730 units, 135 115 polygons (45 118 in bbox) | 116 242 765 B zip (451 813 110 B GML) | IT South Tyrol 98%, IT other 97% | **Recommend** |
| GeoCover vector datasets, sheets 1179/1199/1219/1239 | swisstopo | https://www.geocat.ch/geonetwork/srv/eng/catalog.search#/metadata/2467ab13-e794-4c13-8c55-59fe276398c5 | STAC https://data.geo.admin.ch/api/stac/v1/collections/ch.swisstopo.geologie-geocover (4 `*_2056.gpkg.zip`, HTTP 200) | GeoPackage per sheet | 1:25,000 | swisstopo OGD terms https://www.swisstopo.admin.ch/en/free-geodata-geoservices-terms-use-ogd | Bedrock CHRONO_TOP/BASE (40 German names), unconsolidated RUNC_CHRONO_T/B (4); yes via German-name table | 5 751 bedrock + 2 887 unconsolidated polygons | 35 760 451 B (4 zips) | CH 99% | **Recommend** |
| INSPIRE Geologische Einheiten 1:500.000 Österreich | GeoSphere Austria | https://geoportal.inspire.gv.at/metadatensuche/inspire/api/records/30aa261e-4d45-4470-92b6-bac9c76bb344 | https://gis.geologie.ac.at/inspire/download/insp_ge_gu_sg500_epsg4258.gpkg (HTTP 200) | GeoPackage | 1:500,000 | CC BY 4.0 (ISO record; service copyright) | olderNamedAge/youngerNamedAge, 20 INSPIRE era names in bbox; yes, direct | 4 107 (647 in bbox) | 23 490 560 B | AT 100% | **Recommend** |
| INSPIRE Geologische Einheiten 1:50.000 Österreich | GeoSphere Austria | https://geoportal.inspire.gv.at/metadatensuche/inspire/api/records/b894632e-d8dd-438c-88d3-c68fcf8b6a16 | https://gis.geologie.ac.at/inspire/download/insp_ge_gu_sg50_epsg4258.gpkg (HEAD 200) | GeoPackage | 1:50,000 | CC BY 4.0 | same INSPIRE era fields; yes | 20 820 in 10.3-12.7 E / 46.3-47.2 N | 1 027 649 536 B | AT 37%, IT South Tyrol 9% | Later upgrade, not now |
| INSPIRE Geologische Einheiten 1:200.000 Österreich | GeoSphere Austria | https://geoportal.inspire.gv.at/metadatensuche/inspire/api/records/fbd0d3da-e025-4728-8fd5-22ad5f530511 | https://gis.geologie.ac.at/inspire/download/insp_ge_gu_sg200_epsg4258.gpkg (HEAD 200) | GeoPackage | 1:200,000 | CC BY 4.0 | same; yes | 1 607 in bbox | 234 827 776 B | AT 25% (East Tyrol only) | Reject: partial |
| INSPIRE Geologic Units 1:1,000,000 Austria | GeoSphere Austria | https://geoportal.inspire.gv.at/metadatensuche/inspire/api/records/2fda9875-79de-442e-958b-37bee7c024f1 | https://gis.geologie.ac.at/inspire/download/insp_ge_gu_sg1000_epsg4258.gpkg (downloaded to scratch) | GeoPackage | 1:1,000,000 | CC BY 4.0 | same; yes | 758 (95 in bbox) | 9 621 504 B | AT 100% | Reject: 1:500k covers the same at 2x the detail |
| Geologische Haupteinheiten / Unità geologiche principali (`p_bz-Geology:GeologicalUnitsOverview`) | Prov. Bolzano, Ufficio Geologia e prove materiali | CKAN https://data.civis.bz.it/dataset/unita-geologiche-principali ; ISO uuid p_bz:Geology:GeologicalUnitsOverview | WFS https://geoservices1.civis.bz.it/geoserver/p_bz-Geology/ows (typeName above; HTTP 200) | WFS/GeoJSON | 1:300,000 (ISO denominator), "Modello interpretativo" | **Conflict:** ISO record CC BY-SA 3.0; CKAN license_id cc-zero but its access_constraints extra says CC BY-SA 3.0 | none; only legend text LEG_IT/LEG_DE (71 classes) and tectonic unit | 245 | 556 787 B GeoJSON | 100% of every gap part | Reject: coarse, no age field, licence unclear |
| INSPIRE Unità geologiche (`p_bz-Inspire:GE.GeologicUnit`) | Prov. Bolzano, Ufficio Pianificazione territoriale e cartografia | CKAN https://data.civis.bz.it/dataset/inspire-unita-geologiche-geologic-unit ; ISO uuid p_bz:Inspire:GE.GeologicUnit | WFS https://geoservices8.civis.bz.it/geoserver/p_bz-Inspire/ows (HTTP 200) | WFS/GeoJSON | ISO says 1:10,000, but geometry = the 1:300k overview clipped to the province | CC0 1.0 (ISO + CKAN) | OLDER/YOUNGER_GEOCHRONOLOGIC_ERA, period rank (7 values); yes | 101 | 473 115 B GeoJSON | IT South Tyrol 100% | Fallback only (for ISPRA slivers, or if ISPRA ages are judged unusable) |
| Carta Geologica d'Italia 1:500.000 (`ge-core3:geo500K`) | ISPRA | WFS caps https://sgi2.isprambiente.it/geoserver/ge-core3/wfs?service=wfs&version=2.0.0&request=GetCapabilities | same WFS (HTTP 200) | WFS | 1:500,000 | CC BY 4.0 (service AccessConstraints) | ETAINF/ETASUP English names, 139 of 961 bbox features "n.d" | 10 400 (961 in bbox) | 2 060 150 B GeoJSON (bbox) | IT 100% | Reject: 5x coarser than the 1:100k map |
| EGDI 1:1 Million pan-European Surface Geology | EGDI / GeoZS | https://egdi.geology.cz/record/basic/5f7db57f-6e84-4484-835f-706b0a010833 | https://egeologija.si/download/GeologicUnitView.gpkg (HEAD 200) | GeoPackage / WFS | 1:1,000,000 | CC BY 4.0 | representativeAge_uri only (older/younger "unknown") | 1 046 in bbox (IT-ISPRA 946, AT_GBA 100) | 675 704 832 B | only national 1:1M maps | Reject: coarse, adds nothing to national sources |
| Carta Geologica 250.000 (Lombardia) | Regione Lombardia | https://geodati.gov.it/resource/id/r_lombar:a1cbcd90-f0dd-4af2-88ac-a9fb0ecccf3d | MapServer https://www.cartografia.servizirl.it/expo/rest/services/gpt/cartageo_250/MapServer (HTTP 200); package page on geoportale.regione.lombardia.it (no direct zip link found) | shapefile / MapServer | 1:250,000 (1990) | CC BY 4.0 (RNDT record) | PERIODO text (341 of 878 blank in bbox envelope) | 878 in bbox envelope | not measured | IT other 46% | Reject: ISPRA 100k covers 97% at finer scale |
| Tectonic Map of Switzerland 1:500 000 | swisstopo | STAC ch.swisstopo.geologie-tektonische_karte | `geologie-tektonische_karte_2056_en.gpkg` (HEAD 200) | GeoPackage | 1:500,000 | swisstopo OGD terms | tectonic units, not stratigraphic age | not counted | 23 576 576 B | reaches 11.02 E | Reject: tectonic, coarse |

## 4. Rejected candidates and reasons (checked 2026-09-12)

- **ISPRA CARG 1:50,000 sheets 028, 029, 044, 045, 046**: rejected earlier (no vector database); not re-researched.
- **ISPRA 1:100,000 raster release (2025-09-04)**: raster scans only (https://portalesgi.isprambiente.it/en/?p=8488/). The vector version is the INSPIRE GML recommended above. [verified 2026-09-12]
- **South Tyrol GeologicalUnitsOverview (1:300k)**: interpretive overview, no age field, CC BY-SA 3.0 in the ISO record against CC0 in CKAN. It would fill everything, but coarsely and with licence doubt. [verified 2026-09-12]
- **South Tyrol INSPIRE GE.GeologicUnit**: CC0 with period-rank ages, but it is the overview geometry. All 101 polygons match the 101 overview polygons in the province; 100% of its boundary length lies within ~100 m of overview boundaries. It is kept as a fallback, not as the primary fill. [verified 2026-09-12]
- **South Tyrol CARG GeologicalUnits-Aggregated**: same survey coverage as the detailed layer (see section 1). [verified 2026-09-12]
- **GeoSphere 1:200k / 1:1M**: partial (200k) or redundant with 500k (1M). **GeoSphere 1:50k**: later upgrade (1.03 GB, 37% of the Austrian gap, sheets not edge-matched per its ISO record). [verified 2026-09-12]
- **ISPRA geo500K, ISPRA ONEGE 500K / One_GE_1M** (`ge-core` workspace, layer names only seen), **EGDI 1:1M / OneGeology**: coarser duplicates of national maps. [verified 2026-09-12 for geo500K and EGDI; ge-core layers only listed]
- **Regione Lombardia 1:250k**: open (CC BY 4.0) but partial and older than ISPRA 100k in these areas. [verified 2026-09-12]
- **Friuli Venezia Giulia Carta geologica 1:150.000 (2006)**: offered as a PDF and in a WebGIS; the page states no licence and no vector download (https://www.regione.fvg.it/rafvg/cms/RAFVG/ambiente-territorio/geologia/FOGLIA01/). ISPRA 100k covers this piece. [verified 2026-09-12]
- **swisstopo GeoMaps 500 Vector (Geological Map of Switzerland 1:500k)**: Switzerland only, 1:500k (https://www.swisstopo.admin.ch/en/geomaps-500-vector); not located under a STAC id in this pass (guessed id `ch.swisstopo.geologie-geologische_karte` returned 404). GeoCover is finer for the Swiss strip. [verified 2026-09-12 for the page; STAC id not found]
- **Land Tirol tiris**: the search found only a PDF "Geologische Karte für TIROL" (https://www.tirol.gv.at/fileadmin/applikationen/tiris/tiris-links/bilder/Tirol_Geologie_A3.pdf) and the tiris OGD portal (https://data-tiris.opendata.arcgis.com/); no geological vector dataset. The data.gv.at CKAN API call returned HTML, not JSON. Austrian geology is served by GeoSphere Austria. [from search, not opened]

## 5. Inspection summaries of the downloaded data

### ispra-geologia-100k-inspire (`data/raw/ispra-geologia-100k-inspire/`)

- Files: `Carta_geologica_100k_INSPIRE-GE_nord.zip` (116 242 765 B, sha256 91400fc5...decb2), `GE.atom.en.xml` (Atom dataset feed), `checksums.json`.
- GML: one `GeologicCollection` "Carta geologica 100k", 3 730 `GeologicUnit` (each with one `GeologicEvent`, eventProcess, olderNamedAge, youngerNamedAge as ICS URIs, `gml:description` = original legend text), 135 115 `MappedFeature` polygons in EPSG:4258 with **lat, lon** axis order.
- In the terrain bbox: 45 118 polygons, 1 072 units, extent 9.953-12.953 E / 45.668-47.094 N.
- Most frequent age names in the bbox (older + younger uses): Cenozoic 16 957, Quaternary 16 365, Holocene 6 636, Present 5 404, Permian 4 962, Ladinian 4 672, Precambrian 3 836, Pennsylvanian 3 746, Carnian 3 566, Anisian 2 624, Lower Triassic 2 059, Lopingian 1 440.
- Samples: "arenarie di val gardena" Guadalupian (depositionFromWater); "detrito di falda" Present; "fillade quarzifera di bressanone" Pennsylvanian (metamorphicProcess).
- eventProcess over the 1 072 units: depositionFromWater 403, metamorphicProcess 244, depositionFromMovingFluid 201, intrusion 110, effusiveEruption 64, others below 10.
- Coverage: South Tyrol gap 98% (0.4403 of 0.4481), Italy outside South Tyrol 97% (0.3100 of 0.3181). Bbox boxes from the task: Bletterbach 100%; Bolzano-Brixen strip 75% and Pustertal W 65% (in both boxes the remainder is mostly Austria).

### swisstopo-geocover (`data/raw/swisstopo-geocover/`)

- 4 zips (1179 Samnaun/Ischgl, 1199 Scuol, 1219 S-charl, 1239 Sta Maria/Müstair), each with `GPKG/de` and `GPKG/fr`; checksums in `checksums.json`.
- Layers per sheet: 18 feature tables (points, lines, polygons). Polygons for colouring: `Bedrock_PLG` (fields TECTO, DESCRIPTION, CHRONO_TOP, CHRONO_BASE, LITHO_MAIN, LITSTRAT, ...) and `Unconsolidated_Deposits_PLG` (RUNC_CHRONO_T, RUNC_CHRONO_B, RUNC_LITHO, RUNC_LITSTRAT, ...). CRS EPSG:2056.
- Counts: 5 751 bedrock + 2 887 unconsolidated polygons. Union extent 10.213-10.492 E / 46.531-47.001 N. Swiss gap 99% (0.0633 of 0.0637).
- Top chrono names in bedrock: Ladinien 1 936, Mesozoikum 1 691, Proterozoikum 1 278, Carnien 1 007, Norien 926, Paläozoikum 920. Sample: Roz-Champatsch-Flysch, CHRONO_TOP "Paläogen", CHRONO_BASE "Späte Kreide".

### geosphere-geologicunits-500k (`data/raw/geosphere-geologicunits-500k/`)

- `insp_ge_gu_sg500_epsg4258.gpkg` (23 490 560 B, sha256 8d39d3b3...f46a). Tables: `geologicunitview` / `mappedfeature` (4 107 each), `geologicunit` (65), `geologicevent` (65), `compositionpart` (194). EPSG:4258.
- 647 polygons intersect the bbox. Sample rows: "orthogneiss; Permo-Carboniferous", "siliciclastic rock; Permo-Scythian" (Permian - Lower Triassic), "mainly carbonate rock; Middle Triassic - Jurassic".
- Austrian gap 100% (0.7304 of 0.7310).

## 6. Bibliography row drafts (for research/sources/bibliography.md; not inserted)

| Key | Reference | URL / DOI | Accessed | Open access | Verification | Short cite |
|---|---|---|---|---|---|---|
| geosphere-ge-500k | GeoSphere Austria. INSPIRE Geologische Einheiten 1:500.000 Österreich (Oberflächengeologie); based on the geological base map of the Metallogenetische Karte von Österreich 1:500.000 (GeoSphere Austria 2025, Tethys RDR). GeoPackage insp_ge_gu_sg500_epsg4258. | https://geoportal.inspire.gv.at/metadatensuche/inspire/api/records/30aa261e-4d45-4470-92b6-bac9c76bb344 | 2026-09-12 | CC BY 4.0 | [verified 2026-09-12 - ISO record (licence, lineage); GPKG downloaded and inspected] | GeoSphere Austria geological map 1:500,000 |
| ispra-geologia-100k | ISPRA - Dipartimento Servizio Geologico d'Italia. Carta Geologica d'Italia in scala 1:100.000 - Dataset, harmonised to INSPIRE and GeoSciML (277 sheets surveyed 1880-1980, digitised late 1990s, revised 2005-2009). GML download "Carta_geologica_100k_INSPIRE-GE_nord". | https://geodati.gov.it/resource/id/ispra_rm:Geologia100K_DT | 2026-09-12 | CC BY 4.0 | [verified 2026-09-12 - RNDT record and INSPIRE Atom feed; GML downloaded and inspected] | ISPRA Geological Map of Italy 1:100,000 |
| swisstopo-geocover | Federal Office of Topography swisstopo, Swiss Geological Survey. Geological Vector Datasets GeoCover (Geologische Vektordatensätze GeoCover), 1:25,000; sheets 1179, 1199, 1219, 1239. | https://www.geocat.ch/geonetwork/srv/eng/catalog.search#/metadata/2467ab13-e794-4c13-8c55-59fe276398c5 | 2026-09-12 | Free use, source attribution mandatory (swisstopo OGD terms) | [verified 2026-09-12 - geocat ISO record, STAC collection and OGD terms page; GPKGs downloaded and inspected] | swisstopo GeoCover |

## 7. Uncertainties and open questions

- ISPRA 1:100,000 ages mix formation and metamorphic events, and some unit joins are wrong (section 2). Needs a reviewed mapping table; this is the main risk of the recommendation.
- The CC0 South Tyrol INSPIRE layer republishes geometry whose parent is marked CC BY-SA 3.0. If the fallback is ever used, ask the province (geologia@provincia.bz.it, per the ISO record) which licence applies.
- swisstopo CHRONO_TOP/BASE semantics are inferred from data. The data-model PDF (Geological Datamodel 2D; page link https://www.swisstopo.admin.ch/dam/en/sd-web/Np-QwyB4JAjX/datamodel-de.pdf) could not be rendered here.
- The country split uses 1:500k/1:1M outlines; the Friuli attribution of the eastern piece is by position only.
- GeoSphere 500k lineage author/year (Weber 1997) came from a search snippet [from search, not opened]; the ISO lineage text itself was read [verified 2026-09-12].
- swisstopo licence is not a CC licence; the license register row should quote the OGD terms and the attribution "Federal Office of Topography swisstopo".

## 8. Sources opened (2026-09-12)

- South Tyrol CKAN: https://data.civis.bz.it/api/3/action/package_search?fq=tags:Geologia ; package_show for unita-geologiche-principali and inspire-unita-geologiche-geologic-unit
- South Tyrol GeoNetwork ISO XML: https://geonetwork1.civis.bz.it/geonetwork/srv/api/records/p_bz:Geology:GeologicalUnitsOverview/formatters/xml and .../p_bz:Inspire:GE.GeologicUnit/formatters/xml
- South Tyrol WFS: https://geoservices1.civis.bz.it/geoserver/ows (GetCapabilities), https://geoservices1.civis.bz.it/geoserver/p_bz-Geology/ows , https://geoservices8.civis.bz.it/geoserver/p_bz-Inspire/ows
- ISPRA: https://geodati.gov.it/resource/id/ispra_rm:Geologia100K_DT , https://geodati.gov.it/resource/id/ispra_rm:Geo_100k_DS , https://sgi3.isprambiente.it/download/GE.atom.TOP.en.xml , https://sgi3.isprambiente.it/download/GE.atom.en.xml , https://portalesgi.isprambiente.it/en/?p=8488/ , https://sgi2.isprambiente.it/geoserver/ge-core3/wfs
- GeoSphere Austria: ISO records 30aa261e-4d45-4470-92b6-bac9c76bb344, b894632e-d8dd-438c-88d3-c68fcf8b6a16, fbd0d3da-e025-4728-8fd5-22ad5f530511, 2fda9875-79de-442e-958b-37bee7c024f1 on https://geoportal.inspire.gv.at/ ; https://gis.geosphere.at/maps/rest/services/inspire (MapServer JSON for 50k/200k/500k/1M); Atom service feed https://geometadatensuche.inspire.gv.at/metadatensuche/inspire/atom/describe/service?uuid=D3AAC068-0E09-4786-80C0-58602F9BA9F4
- swisstopo: https://data.geo.admin.ch/api/stac/v1/collections , https://www.geocat.ch/geonetwork/srv/api/records/2467ab13-e794-4c13-8c55-59fe276398c5/formatters/xml , https://www.swisstopo.admin.ch/en/free-geodata-geoservices-terms-use-ogd , https://www.swisstopo.admin.ch/en/geological-model-2d-geocover , https://www.swisstopo.admin.ch/en/geomaps-500-vector
- EGDI: https://egdi.geology.cz/record/basic/5f7db57f-6e84-4484-835f-706b0a010833 ; WFS https://geoserver.geo-zs.si/egdi-surface-geology/gsmlp/wfs
- Lombardia: https://geodati.gov.it/resource/id/r_lombar:a1cbcd90-f0dd-4af2-88ac-a9fb0ecccf3d ; https://www.cartografia.servizirl.it/expo/rest/services/gpt/cartageo_250/MapServer
- Friuli Venezia Giulia: https://www.regione.fvg.it/rafvg/cms/RAFVG/ambiente-territorio/geologia/FOGLIA01/
