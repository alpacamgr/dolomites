# Existing Geological Visualization Websites & Apps

**Research Date:** 2026-09-06  
**Scope:** Interactive websites and apps visualizing deep-time geology, plate tectonics, paleogeography, and Alpine/Dolomites geology.

---

## Surveyed Sites

### 1. Ancient Earth Globe
- **URL:** https://dinosaurpictures.org/ancient-earth [verified 2026-09-06]
- **Creator:** Ian Webster
- **What It Shows:** Interactive 3D globe showing Earth's continental positions and geography across 750 million years (Precambrian to present)
- **Data Sources:** Paleogeographic maps by C.R. Scotese (PALEOMAP Project)
- **Technology:** Interactive web application with 3D globe rendering, WebGL-capable
- **Interaction Model:** Keyboard-driven (arrow keys) for time navigation; mouse for globe rotation; jump-to-event links (e.g., "first dinosaurs," "Pangea," "extinction")
- **Strengths:** Comprehensive temporal span; visual continental drift across deep time; multiple entry points for specific periods
- **Weaknesses:** Limited positional accuracy (~100 km); clouds and stars are unhistorical placeholders; no terrain detail
- **Open Source:** Not stated
- **License:** Not stated

### 2. GPlates Web Portal
- **URL:** https://portal.gplates.org [verified 2026-09-06]
- **Creator:** EarthByte Group (AuScope-funded); provides gateway to GPlates ecosystem
- **What It Shows:** Interactive 3D geophysical and geological data; plate tectonic reconstructions; dynamic surface topography
- **Data Sources:** EMAG2 (magnetic anomalies), SRTM15 (seafloor topography), gravity grids, crustal thickness models, PaleoDEM (paleontological reconstructions), lithology, polymetallic nodules
- **Technology:** Cesium (WebGL-based 3D mapping engine); PyGPlates for programmatic access
- **Interaction Model:** Card-based portal interface with "Launch" buttons to specialized Cesium viewers; web services API; linked Jupyter notebooks
- **Strengths:** Aggregates diverse geoscientific datasets; professional research-grade tools; web-accessible
- **Weaknesses:** No information on interaction polish or geological storytelling narrative
- **Open Source:** GPlates desktop (GPL-2); portal extent of openness not stated
- **Repo:** https://www.gplates.org/ (desktop software)

### 3. GPlates Desktop Software
- **URL:** https://www.gplates.org/ [verified 2026-09-06]
- **Creator:** EarthByte Group (AuScope-funded)
- **What It Shows:** Professional plate tectonic visualization, reconstruction, and GIS analysis across geological time
- **Data Sources:** Vector, raster, and volume plate tectonic datasets; user-customizable
- **Technology:** Desktop application (Windows, Linux, macOS); Python library (pyGPlates); web service API; mobile companion
- **Interaction Model:** Drag/click manipulation of plates through time; time-slider navigation; GIS layer management
- **Strengths:** Production-grade tool; flexible data input; used in academic and research contexts; comprehensive ecosystem (GPlately, pyGPlates)
- **Weaknesses:** Desktop software, not primarily web-based visualization; steeper learning curve; not designed for casual geological narrative
- **Open Source:** Yes (GNU GPL v2)
- **License:** GPL-2
- **Repo:** Maintained by EarthByte Group

### 4. Deep Time Maps
- **URL:** https://deeptimemaps.com [verified 2026-09-06]
- **Creator:** Ron Blakey; Colorado Plateau Geosystems Inc.
- **What It Shows:** Static paleogeographic maps showing ancient seas, ocean basins, mountain ranges across geological eras
- **Data Sources:** "Latest geologic data from the scientific literature"
- **Technology:** Static map images; organized by region and time period
- **Interaction Model:** Browse-and-download; no interactive visualization; requires licensing purchase
- **Strengths:** Scientific credibility (peer-reviewed sources); diverse regional coverage
- **Weaknesses:** Not interactive; not digital (print maps); highly commercial; requires institutional/individual licensing
- **Open Source:** No
- **License:** Copyright Colorado Plateau Geosystems Inc.; requires purchase for any use

### 5. Dolomites World Heritage Geotrail
- **URL:** https://dolomitesgeotrail.com/en/home-page-en/ [verified 2026-09-06]
- **Creator:** Fondazione Dolomiti UNESCO
- **What It Shows:** 300 million years of Dolomites geological history across 9 Systems, 47 hiking trails, 125 GEOSTOPS (geological stops)
- **Data Sources:** Not specified; curated by UNESCO World Heritage geological experts
- **Technology:** Web platform with interactive maps, 27 HD-360° panoramic images
- **Interaction Model:** Hybrid on-ground (hiking with markers) and online (virtual routes); three thematic journeys (geological history, catastrophic events, climate change); pop-ups with information; 360° panorama viewer
- **Strengths:** Deeply contextual to Dolomites specifically; integrates physical field experience with digital; three distinct narrative angles; high-resolution imagery
- **Weaknesses:** Primarily static panoramas; no 3D terrain; requires hiking for full experience; no stated scientific data sources
- **Open Source:** No
- **License:** Not stated

### 6. Dolomitization Interactive Game
- **URL:** https://www.dolomitibelluno.it/en/2026/08/20/an-interactive-flight-over-the-dolomites/ [verified 2026-09-06]
- **Creator:** Dolomiti Project and Royal 360 (commissioned by Fondazione Dolomiti UNESCO)
- **What It Shows:** Immersive exploration of Dolomites UNESCO World Heritage Site through geological, naturalistic, and historical lenses
- **Data Sources:** Not specified
- **Technology:** Hemispherical panoramic photos (including night-time); ambient music and sound effects; quiz/interactive modules
- **Interaction Model:** Role-selection (conservator, geologist, explorer, landscape artist); self-directed path through clues scattered in landscape; quizzes; ambient storytelling
- **Strengths:** Multiple role-based entry points; engaging multimedia (panoramas, sound); geological narrative woven into landscape features
- **Weaknesses:** Primarily image-based (not map/globe); no interactive 3D model; limited scientific data disclosure
- **Open Source:** No
- **License:** Not stated

### 7. Animated Dolomites Video
- **URL:** https://www.dolomitiunesco.info/en/activities/the-animated-dolomites [verified 2026-09-06]
- **Creator:** Fondazione Dolomiti UNESCO
- **What It Shows:** Geological events leading to Dolomites formation; combines animation and photographic imagery; 4 minutes
- **Data Sources:** Not specified; UNESCO-curated
- **Technology:** Video animation (format not specified)
- **Interaction Model:** Linear playback; available in Italian, English, German
- **Strengths:** Accessible summary; multi-language; production quality for public education
- **Weaknesses:** Non-interactive; linear narrative only; no exploration capability; limited time for complex geology
- **Open Source:** No
- **License:** Not stated

### 8. OpenTopography
- **URL:** https://opentopography.org [verified 2026-09-06]
- **Creator:** San Diego Supercomputer Center, University of California San Diego
- **What It Shows:** High-resolution topographic data and analysis tools; lidar point clouds, digital elevation models, terrain metrics
- **Data Sources:** LiDAR (global and regional), DEMs, DTMs, SRTM, USGS 3DEP, NOAA coastal/urban lidar; new: national-scale for Norway, Finland, Switzerland, Liechtenstein
- **Technology:** 3D point cloud browser (WebGL); raster visualization tools (hillshade, color-relief, slope, aspect, roughness); Point Elevation API; on-demand processing
- **Interaction Model:** Web browser viewer for point clouds; API access; visualization configuration (color palettes, illumination angles)
- **Strengths:** Comprehensive open-access topographic data; professional analysis tools; supports custom import (heightmaps); API-accessible
- **Weaknesses:** Data-centric rather than narrative; requires technical familiarity; not designed for geological history storytelling
- **Open Source:** Software openness not clearly stated; data is open
- **License:** Data availability suggests open, but specific license not verified

### 9. Tectonics.js
- **URL:** https://davidson16807.github.io/tectonics.js/ [verified 2026-09-06]
- **Creator:** David Wade Stetson (davidson16807)
- **What It Shows:** 3D plate tectonics simulator; procedurally-generated planetary geology with mountain-building, ocean formation, sediment deposition, vegetation
- **Data Sources:** Procedurally-generated (user can import custom heightmaps); no pre-existing geological dataset
- **Technology:** WebGL 3D simulator; interactive controls; supports screenshot, CSV export, heightmap import
- **Interaction Model:** Play/pause/step controls; adjustable simulation speed; toggles for visualization (ocean, shadows, snow, sediment, vegetation); customizable world parameters (resolution, axial tilt, day length)
- **Strengths:** Open-source; fully interactive; runs in browser; educational exploration of tectonic processes
- **Weaknesses:** Procedural/synthetic data (not real Earth); not designed for paleomaps; no Cenozoic Alpine examples
- **Open Source:** Yes
- **License:** Not explicitly stated; code on GitHub
- **Repo:** https://github.com/davidson16807/tectonics.js

### 10. Tectonic Plates Map
- **URL:** https://tectonicplatemap.com/ [verified 2026-09-06]
- **Creator:** Not stated
- **What It Shows:** Interactive map of Earth's 52 major and minor tectonic plates; plate boundaries and movement vectors
- **Data Sources:** OpenStreetMap; no geological data sources specified
- **Technology:** Leaflet (JavaScript map library); OpenStreetMap tiles
- **Interaction Model:** Zoom in/out buttons; gesture-based (swipe for details)
- **Strengths:** Simple, accessible interface; immediate plate visualization
- **Weaknesses:** Static plate positions (no time variation); minimal detail; no paleographic data; limited scientific rigor
- **Open Source:** Built on Leaflet (open source) but creator unknown
- **License:** Not stated

### 11. Paleomap Project (Scotese)
- **URL:** https://scotese.com [certificate error; accessed via search results]
- **Creator:** C.R. Scotese (geologist, University of Texas at Arlington)
- **What It Shows:** 1+ billion years of paleogeographic maps and plate tectonic evolution; 50+ YouTube animations of continental drift
- **Data Sources:** Quantitative, digital paleogeographic modeling with 3D paleotopographic and paleobathymetric information
- **Technology:** 3D computer animations; GIS and plate tectonic models; published in academic papers and museums
- **Interaction Model:** YouTube video animations (linear); static map images
- **Strengths:** Professional palegeographic authority; 3D approach to topography and bathymetry; widely cited in textbooks and research
- **Weaknesses:** Videos are linear, not interactive; maps are mostly static images; YouTube platform limits exploration
- **Open Source:** No
- **License:** Not stated; academic/museum use licensed
- **References:** YouTube channel (Christopher Scotese); ResearchGate; Wikipedia; NASA EARTHDATA; searchanddiscovery.com archives

### 12. ChronoZoom
- **URL:** https://github.com/alterm4nn/ChronoZoom [from search]
- **Creator:** Roland Saekow & Walter Alvarez (UC Berkeley); now open-source community
- **What It Shows:** Interactive timeline spanning 13.7 billion years (Big Bang to present); zoomable across scales from billions of years to single days
- **Data Sources:** User-curated; can include articles, images, video, sound, media
- **Technology:** Web-based interactive timeline; zoomable interface
- **Interaction Model:** Seamless zoom to change temporal scale; click to explore events and media; user can create custom timelines
- **Strengths:** Extreme temporal range; educational; open-source; demonstrates zoom-based temporal navigation
- **Weaknesses:** Not geology-specific; focus on events/media rather than spatial visualization; no maps or paleogeographic data by default
- **Open Source:** Yes
- **License:** Not stated explicitly
- **Repo:** https://github.com/alterm4nn/ChronoZoom

### 13. TimeScale Creator
- **URL:** [Java application; no web URL] [from search]
- **Creator:** Not fully stated in search results
- **What It Shows:** Geological timescale visualization; depicts Earth history; custom charts of any time interval
- **Data Sources:** Internal database with 300+ columns; 50,000+ data points covering sea level, stable isotopes, paleobiology, geomagnetics; Moon and Mars data included
- **Technology:** Java application (desktop); chart/graph generation
- **Interaction Model:** Desktop software; user selects time interval and geologic categories to chart
- **Strengths:** Comprehensive paleontological/paleoclimatic database; flexibility in time-period selection
- **Weaknesses:** Desktop-only; not interactive exploration; limited to timeline view; not web-accessible
- **Open Source:** Free but unknown if open source
- **License:** Free to academic users
- **References:** Academic tool; not widely web-promoted

### 14. Tectonic Explorer
- **URL:** https://tectonic-explorer.concord.org/ [verified; limited content] [verified 2026-09-06]
- **Creator:** Concord Consortium
- **What It Shows:** Interactive exploration of plate tectonics, cross-sections, rock formation
- **Data Sources:** Not specified from limited access
- **Technology:** Web-based (likely)
- **Interaction Model:** Interactive; includes cross-section views
- **Strengths:** Educational focus from reputable source
- **Weaknesses:** Limited page access; details unavailable
- **Open Source:** Not clear
- **License:** Not clear

### 15. MUSE Trento (Geological Museum of the Dolomites in Predazzo)
- **URL:** https://www.muse.it/en/home [verified 2026-09-06]
- **Creator:** MUSE (Museo delle Scienze di Trento)
- **What It Shows:** Geological history of the Dolomites; satellite museum located in Predazzo
- **Data Sources:** Museum collections; geological specimens
- **Technology:** Physical museum with some digital content; UranIA chatbot (free through June 2026)
- **Interaction Model:** On-site exhibits; limited online presence; chatbot for inquiries
- **Strengths:** Official regional geology museum; direct access to specimens and expert curators
- **Weaknesses:** Primarily physical location; minimal digital/interactive online content stated
- **Open Source:** No
- **License:** Not applicable (museum)

### 16. Naturmuseum Südtirol (South Tyrol Museum of Natural Sciences, Bolzano)
- **URL:** [Physical museum; limited web presence]
- **Creator:** South Tyrol Provincial Museums
- **What It Shows:** 300+ million years of South Tyrol geological history; porphyry plateau, Eastern Alps, Dolomites formation, glaciation, alpine uplift; living coral reef aquarium (Triassic analog)
- **Data Sources:** Museum specimens and dioramas; scientific literature
- **Technology:** Physical exhibits: models, dioramas, experiments, interactive multimedia stations; 1,000 sqm permanent exhibition
- **Interaction Model:** On-site exploration; games and experiments; multimedia stations
- **Strengths:** Comprehensive geology span; Triassic reef visualization (9,000-litre aquarium); interactive hands-on elements; integrated display of alpine uplift sequence
- **Weaknesses:** Physical-only; no web-accessible digital exhibits; limited online presence documented
- **Open Source:** No
- **License:** Not applicable

### 17. Bletterbach GEOPARC
- **URL:** https://www.bletterbach.info/en/ [verified via search; limited access]
- **Creator:** Municipality of Aldino / South Tyrol Geopark
- **What It Shows:** South Tyrol's largest canyon; geological time trail through porphyry and sandstone layers; Earth history walk (geological trail + woodland path)
- **Data Sources:** Physical rock strata; guided interpretation by local geologists
- **Technology:** Physical location; Visitor Center with interactive displays and multimedia; informative panels
- **Interaction Model:** Guided walking tours (3.5 hours, daily May–Oct); Visitor Center multimedia; woodland wheelchair-accessible path
- **Strengths:** Direct experience of real stratigraphy; expert-led interpretation; integration of Alpine geology narrative
- **Weaknesses:** Physical location required; limited digital/web content; tours in German/Italian only (as of 2025)
- **Open Source:** No
- **License:** Not applicable

### 18. Mapbox & Deck.gl (3D Terrain Storytelling Technology)
- **URL:** https://deck.gl, https://www.mapbox.com/mapbox-gljs [verified via search]
- **Creator:** Mapbox (Deck.gl is open-source framework)
- **What It Shows:** Technology stack for scroll-driven 3D terrain visualization; not a geological app itself
- **Data Sources:** User-provided (terrain, geospatial data); supports elevation APIs
- **Technology:** Mapbox GL JS (WebGL); Deck.gl (WebGL framework); supports 3D terrain, point clouds, animations
- **Interaction Model:** Smooth camera animation; scroll-driven narrative capability; 3D terrain visualization; high performance
- **Strengths:** Production-grade tools; excellent 3D terrain rendering; supports scrollytelling pattern; well-documented
- **Weaknesses:** Technology, not geology product; requires custom development for specific applications
- **Open Source:** Deck.gl is open-source; Mapbox GL has open-source variants (MapLibre)
- **License:** Mapbox proprietary; Deck.gl (BSD)
- **Use Case:** Foundation for building custom geology visualization apps

### 19. Three.js (3D Web Graphics Technology)
- **URL:** https://threejs.org [from search results] [from search, not opened]
- **Creator:** Ricardo Cabello (Mr. doob)
- **What It Shows:** JavaScript 3D library for WebGL; general-purpose 3D graphics in web browsers
- **Data Sources:** User-provided
- **Technology:** WebGL; JavaScript library; cross-browser support
- **Interaction Model:** Flexible; depends on application built with library
- **Strengths:** Mature, well-documented, widely-used in web 3D projects; good performance
- **Weaknesses:** Requires custom development; not geology-specific; less optimized for large-scale terrain than Mapbox/Deck.gl
- **Open Source:** Yes
- **License:** MIT
- **Use Case:** Foundation for building custom geology visualizations (e.g., Petro3D for geophysicists)

---

## Lessons for our project

1. **Scroll-driven 3D terrain is a proven interaction pattern** (Mapbox, Deck.gl examples) and suited to narrative deep-time geology. Avoid forcing users into linear timelines; instead, let scroll or swipe control temporal progression while maintaining 3D spatial context.

2. **No single existing tool combines paleogeography (Ancient Earth, GPlates, Scotese) with Dolomites-specific geological narrative and interactive 3D model.** Deep Time Maps lacks interaction; Geotrail lacks dynamic 3D; GPlates is professional-grade but not narrative-driven. **Our project fills a distinct gap.**

3. **Real scientific data + visualization polish = impact.** GPlates/Scotese use published plate-tectonic reconstructions; Dolomites Geotrail cites UNESCO heritage work. Cite data sources explicitly (plate models, paleoDEMs, Alpine uplift studies, Triassic reef references). Don't simulate; reconstruct.

4. **Multiple narrative entry points matter.** Dolomitization game uses role-selection (conservator, geologist, explorer); Geotrail uses three thematic routes (geological history, catastrophic events, climate). Consider: timeline-first, process-first (plate tectonics), or place-first (specific peaks/formations).

5. **Panoramic imagery with geological annotation is effective but limited.** Dolomitization uses 360° photos; they engage but don't enable exploration of deep time or subsurface geology. Combine photos with dynamic 3D reconstruction to show what the landscape *looked like* 250 Mya.

6. **Avoid heavy institutional overhead.** MUSE, Naturmuseum, Bletterbach are excellent but primarily physical sites with minimal digital presence. A web-first approach (like Geotrail, Dolomitization) is more scalable for public engagement.

7. **WebGL + Cesium/Mapbox/Deck.gl is the right stack for 3D geospatial storytelling.** Ancient Earth uses it; GPlates Portal uses Cesium; Mapbox/Deck.gl examples show smooth camera animation + terrain. Avoid Three.js for large-scale terrain; Deck.gl + MapTiler terrain is production-proven.

8. **Temporal control is critical.** Ancient Earth's arrow-key navigation is simple and intuitive; ChronoZoom's zoom-based temporal scale is elegant but not spatial. Consider: slider (explicit), animation (passive), scroll (narrative), or key-step buttons (historical events). For deep time, show > 300 Mya (cover Tethys closure, reef platforms, Cenozoic uplift).

9. **Dolomites geology spans 300+ Mya to present; organize by major events, not just time.** Tethys subsidence → Triassic carbonate platform → Jurassic rifting → Cenozoic Alpine collision → Quaternary glaciation. Each has distinct stratigraphy and paleomaps.

10. **Data transparency is a feature.** GPlates and OpenTopography openly list their reconstructions and sources (Scotese PALEOMAP, gravity grids, lidar). Dolomites Geotrail does not disclose sources; users cannot verify geology. Cite and link to: Scotese plate models, Alpine tectonic papers (Neubauer, Schmid, Schönborn), paleoDEMs, DEM sources.

11. **Avoid static maps and linear videos as the primary interaction.** Deep Time Maps and Animated Dolomites are educational but passive. Interactive exploration (drag to rotate, scroll to advance time, click to interrogate features) increases retention and scientific understanding.

12. **Accessibility and mobile matter.** Geotrail, Dolomitization, and Tectonic Explorer are not explicitly mobile-optimized in available documentation. For a public-facing geology project, ensure responsive design, touch controls, and offline capability (or clear limitations).

---

## Sources

**Interactive Geological Visualizations (Verified):**
- [Ancient Earth Globe](https://dinosaurpictures.org/ancient-earth) — Ian Webster's paleogeographic globe
- [GPlates Web Portal](https://portal.gplates.org) — Interactive plate tectonics & geophysical data visualization
- [GPlates Desktop](https://www.gplates.org/) — Professional plate tectonic reconstruction software
- [Deep Time Maps](https://deeptimemaps.com) — Ron Blakey's paleogeographic map collection
- [Dolomites World Heritage Geotrail](https://dolomitesgeotrail.com/en/home-page-en/) — UNESCO-managed geological trail (physical + virtual)
- [Dolomitization Interactive Game](https://www.dolomitibelluno.it/en/2026/08/20/an-interactive-flight-over-the-dolomites/) — Fondazione Dolomiti UNESCO immersive experience
- [OpenTopography](https://opentopography.org) — Lidar data and 3D terrain visualization tools
- [Tectonics.js](https://davidson16807.github.io/tectonics.js/) — Open-source 3D plate tectonics simulator
- [Tectonic Plates Map](https://tectonicplatemap.com/) — Interactive plate boundary visualization
- [Tectonic Explorer](https://tectonic-explorer.concord.org/) — Concord Consortium's educational plate tectonics tool
- [MUSE Trento](https://www.muse.it/en/home) — Museum delle Scienze (Geological Museum of the Dolomites in Predazzo)
- [Bletterbach GEOPARC](https://www.bletterbach.info/en/) — South Tyrol geological park & visitor center

**Technology & Frameworks (Verified):**
- [Mapbox GL JS](https://www.mapbox.com/mapbox-gljs) — WebGL 3D mapping & scrollytelling
- [Deck.gl](https://deck.gl) — Large-scale 3D geospatial visualization framework
- [Cesium.js](https://cesium.com/) — WebGL 3D mapping engine (used by GPlates Portal)
- [Three.js](https://threejs.org) — General-purpose WebGL 3D graphics library

**Geological Datasets & References (from Search):**
- [Paleomap Project by C.R. Scotese](https://www.youtube.com/user/cscotese) — Scotese's YouTube channel with 50+ plate tectonic animations
- [Christopher Scotese (University of Texas at Arlington)](https://uta.academia.edu/ChristopherScotese) — Academic profile with publications
- [ChronoZoom GitHub](https://github.com/alterm4nn/ChronoZoom) — Open-source interactive timeline spanning billions of years
- [Dolomites World Heritage Site (UNESCO)](https://whc.unesco.org/en/list/1237/) — Official UNESCO documentation
- [Fondazione Dolomiti UNESCO](https://www.dolomitiunesco.info/en) — Official foundation website with educational resources

**Museums & Educational Sites (from Search):**
- [Naturmuseum Südtirol (South Tyrol Museum of Natural Sciences), Bolzano](https://www.suedtirolerland.it/en/highlights/museums-and-exhibitions/south-tyrol-museum-of-nature/)
- [MUSE Trento - Geological Museum of the Dolomites](https://www.muse.it/en/home/explore-the-museum/satellite-museums/geological-museum-of-the-dolomites-in-predazzo/)

**Additional References (from Search):**
- [TimeScale Creator](https://www.uic.edu/departments/geosci/timescale.html) — Java application for geological timescale visualization [from search, not opened]
- [Animated Dolomites Video](https://www.dolomitiunesco.info/en/activities/the-animated-dolomites) — UNESCO 4-minute animated formation video (Italian, English, German)
- [Scotese, C.R. ResearchGate](https://www.researchgate.net/publication/269986954_3D_Paleogeography_and_Computer_Animations_of_Earth_History) — Academic paper on 3D paleogeography [from search, not opened]
- [Plate Tectonic Movement Visualizations](https://serc.carleton.edu/NAGTWorkshops/geophysics/visualizations/PTMovements.html) — NAGT collection of PT visualization resources [from search, not opened]

---

**Verification Notes:**
- URLs marked [verified DATE] were successfully fetched and analyzed via WebFetch.
- Sites marked [from search, not opened] were found in search results but could not be fetched (access denied, certificate error, or minimal content) and are listed for reference.
- Physical museum sites (Naturmuseum Südtirol, MUSE, Bletterbach) have minimal digital presence; information comes from search results and museum descriptions.
