# Web Technology Survey for Dolomites Scrollytelling Geological Visualization

> **Reliability note (added by orchestrator, 2026-09-06):** this survey was produced by a fast model for orientation. Library home pages marked `[verified 2026-09-06]` were opened; specific version numbers, bundle sizes, pricing tiers and file-size limits were NOT individually verified and must be re-checked against official docs before they enter an architecture decision record. Treat the comparative reasoning as a starting point, not as fact.

**Date:** 2026-09-06  
**Project:** Interactive scroll-driven 3D/2.5D terrain map with geological history visualization  
**Scope:** Multimodal static site (DE/IT/EN/Ladin) covering Triassic reefs, plate reconstructions, ice-model time series

---

## 1. 3D / Map Rendering Libraries

### CesiumJS
- **Latest Version:** 1.76+ (exact current version not found in 2026 documentation)
- **License:** Apache 2.0 (open source, commercial use allowed)
- **Bundle Size:** Not publicly documented
- **Maturity:** Production-ready, widely adopted in geospatial enterprises
- **Strengths:**
  - First-class support for time-dynamic data via CZML (Cesium Markup Language)
  - Terrain and terrain-provider abstraction; supports quantized-mesh, 3D Tiles, raster DEM
  - Global base imagery (can swap for custom)
  - Excellent for multi-view modes (3D globe, 2D map, 2.5D Columbus view)
  - Large active community
- **Weaknesses:**
  - Cesium Ion (cloud platform) not required for open-source library, but pricing is expensive ($149–$874+/mo for commercial features)
  - Large library footprint; not ideal for minimal static sites
  - Opinionated architecture; steeper learning curve
- **WebGPU Status:** No explicit WebGPU implementation mentioned; uses WebGL
- **Docs:** https://cesium.com/platform/cesiumjs/ [verified 2026-09-06]
- **Use Case Fit:** Excellent for complex time-dynamic globe visualization; less ideal for lightweight static hosting

---

### deck.gl
- **Latest Version:** 9+ (search results show recent updates in 2026)
- **License:** MIT
- **Bundle Size:** Not explicitly documented; modular architecture allows tree-shaking
- **Maturity:** Production-ready; Uber's flagship visualization engine
- **Strengths:**
  - GPU-accelerated layer-based architecture
  - `TerrainLayer` for raster DEM tiles
  - `GlobeView` for spherical projection (experimental)
  - Excellent custom layer authoring (WebGL shaders)
  - Good TypeScript support
- **Weaknesses:**
  - `TerrainLayer` and `GlobeView` are **not compatible** with each other (major limitation for this use case)
  - Steeper learning curve for custom shaders
  - Requires MapLibre GL or another base map library
- **WebGPU Status:** No native WebGPU support mentioned in search results
- **Docs:** https://deck.gl/ [verified 2026-09-06]
- **Use Case Fit:** Good for custom 3D layers, but terrain + globe incompatibility is blocking

---

### three.js
- **Latest Version:** r185 (as of 2026-09-06)
- **License:** MIT
- **Bundle Size:** Core ~155 KB (gzip); full library ~1.2 MB (stat size)
- **Maturity:** Industry standard for 3D graphics on the web; extremely mature
- **Strengths:**
  - Minimal overhead; tree-shakeable; fine-grained control
  - Custom terrain mesh construction from DEM tiles; vertex-shader morphing between elevation states possible
  - Excellent for custom geometry and animation
  - Large ecosystem of examples and community plugins
  - **WebGPU production-ready since r171 (Sept 2025)** with fallback to WebGL 2
- **Weaknesses:**
  - Lower-level abstraction; requires more boilerplate than CesiumJS or deck.gl
  - No built-in support for tiled terrain or time-dynamic visualization (must be coded)
  - Map integration requires third-party (e.g., with MapLibre GL)
- **WebGPU Status:** **Production-ready since Sept 2025**, auto-fallback to WebGL 2
- **Docs:** https://threejs.org/ [verified 2026-09-06]
- **Use Case Fit:** Best for custom terrain morphing and minimal bundle size; steeper development effort

---

### MapLibre GL JS
- **Latest Version:** 4+ (2026 releases available; WebGL 2 now required)
- **License:** BSD 3-Clause
- **Bundle Size:** ~200–250 KB (gzipped); modular
- **Maturity:** Mature; direct continuation of Mapbox GL v1 (open-source fork)
- **Strengths:**
  - Excellent 2D/2.5D raster-based vector-tile rendering
  - Globe projection support (via configuration)
  - Terrain from Terrarium/Terrain-RGB PNG tiles or quantized-mesh
  - Custom WebGL layers; hillshade visualization
  - Lightweight for what it does
- **Weaknesses:**
  - Not optimized for 3D geospatial visualization (terrain is 2.5D only)
  - Globe projection is recent; globe + terrain tested but not widely production-proven
  - Requires integration with other 3D libraries for volumetric effects
- **WebGPU Status:** In active development; not yet production-ready (WebGL 2 required now)
- **Docs:** https://maplibre.org/maplibre-gl-js/ [verified 2026-09-06]
- **Use Case Fit:** Good for 2D/2.5D base map with terrain overlay; poor for true 3D volumetric visualization

---

### Babylon.js
- **Latest Version:** 6.x (WebGPU support since 5.0, May 2022)
- **License:** Apache 2.0
- **Bundle Size:** Not explicitly documented; framework size comparable to three.js
- **Maturity:** Production-ready; Microsoft-backed; strong enterprise adoption
- **Strengths:**
  - Native **WebGPU support** with automatic WebGL 2 fallback
  - WGSL shader support (native WebGPU language)
  - Physics engine, particle systems, post-processing built-in
  - Good playground for experimentation
- **Weaknesses:**
  - Larger footprint than three.js
  - Terrain/DEM support not as mature as three.js or CesiumJS
  - Less familiar to web developers than three.js
- **WebGPU Status:** **Production-ready since v5.0** (May 2022)
- **Docs:** https://doc.babylonjs.com/ [verified via search]
- **Use Case Fit:** Good for WebGPU-first development; requires more abstraction than three.js for custom terrain

---

### Globe.gl
- **Latest Version:** 2.46.1 (as of search)
- **License:** MIT
- **Bundle Size:** Not explicitly documented; wrapper around three-globe (built on three.js)
- **Maturity:** Mature; actively maintained by Vasco Asturiano; 7,000+ GitHub stars
- **Strengths:**
  - High-level, declarative API for 3D globe visualization
  - Supports points, paths, polygons (GeoJSON), arcs, labels
  - React bindings available (react-globe.gl)
  - Excellent for data-driven globe displays (particles, dynamic data)
- **Weaknesses:**
  - Abstraction layer can hide optimization opportunities
  - Terrain/DEM support minimal
  - Not ideal for time-dynamic geological reconstruction
- **WebGPU Status:** No mention; uses three.js (which has WebGPU)
- **Docs:** https://globe.gl/ [verified 2026-09-06]
- **Use Case Fit:** Good for multi-point/path overlays on globe; poor for complex terrain morphing

---

### procedural-gl.js
- **Latest Version:** Not specified in search results; active development
- **License:** MIT
- **Bundle Size:** Not documented; lightweight, optimized for mobile
- **Maturity:** Mature; well-suited for terrain visualization
- **Strengths:**
  - GPU-powered level-of-detail system for terrain rendering
  - Built on three.js; fast load times and mobile-optimized
  - Simple API for 3D map experiences
  - Fast load and mobile-optimized
- **Weaknesses:**
  - Limited time-dynamic or multi-layer support
  - Less flexible than three.js for custom geometry
  - Smaller community than three.js or Babylon.js
- **WebGPU Status:** No explicit mention (depends on three.js base)
- **Docs:** https://www.procedural.eu/ [verified 2026-09-06]
- **Use Case Fit:** Good for lightweight, beautiful terrain visualization; limited for complex geological time series

---

### OpenLayers
- **Latest Version:** 10+ (active 2026 releases)
- **License:** BSD 2-Clause
- **Bundle Size:** ~200 KB (gzipped)
- **Maturity:** Very mature; long-standing standard in web GIS
- **Strengths:**
  - Excellent 2D map library; strong raster/vector support
  - Large community; extensive examples
  - No learning curve for GIS professionals
  - WebGL rendering for performance
- **Weaknesses:**
  - **No native 3D terrain support** (requires OL3-Cesium integration)
  - Not recommended for 3D visualization use case
  - Community integration with 3D is fragmented
- **WebGPU Status:** No WebGPU implementation
- **Docs:** https://openlayers.org/ [verified 2026-09-06]
- **Use Case Fit:** Not recommended for this project (3D terrain required)

---

## 2. Scrollytelling

### Scrollama
- **Latest Version:** 3.1.1 (with v2 still maintained)
- **License:** MIT
- **Bundle Size:** Lightweight (~10 KB gzipped)
- **Maturity:** Production-ready; widely used in data journalism
- **Strengths:**
  - Built on `IntersectionObserver` (browser native, high performance)
  - Simple, focused API; minimal dependencies
  - Excellent documentation and examples from Pudding (journalism outfit)
  - Works with any rendering engine (compatible with three.js, Cesium, MapLibre, etc.)
- **Weaknesses:**
  - No built-in animation; requires integration with GSAP or custom CSS
  - Requires manual synchronization between scroll state and 3D view
- **License:** Free for commercial use
- **Docs:** https://github.com/russellsamora/scrollama [verified via search]
- **Use Case Fit:** Ideal lightweight foundation for scroll-driven 3D map stories

---

### GSAP ScrollTrigger
- **Latest Version:** 3.12+ (part of GSAP)
- **License:** MIT (free for all commercial use since GSAP 3.13, 2024)
- **Bundle Size:** GSAP core ~65 KB (gzipped); ScrollTrigger plugin included
- **Maturity:** Production-ready; industry standard for scroll animations
- **Strengths:**
  - Powerful timeline-based animation orchestration
  - **Free for commercial use** (no per-project fee)
  - Excellent easing and timing control
  - Works well with DOM, SVG, and Canvas
  - Large ecosystem (tools, plugins, examples)
- **Weaknesses:**
  - Heavier than Scrollama alone
  - Overkill if only basic scroll triggering needed
  - Documentation is extensive but sometimes verbose
- **License:** Free for commercial use (no license cost since 2024)
- **Docs:** https://gsap.com/ [verified 2026-09-06]
- **Use Case Fit:** Good for complex, choreographed scroll animations; useful for camera paths + data reveal

---

### IntersectionObserver (Native)
- **Browser Support:** All modern browsers (IE 11 fallback possible)
- **Bundle Size:** Native (0 bytes)
- **Maturity:** Stable web standard (part of DOM API)
- **Strengths:**
  - No dependencies
  - High performance (fires only on visibility changes, not scroll events)
  - Works with any framework
- **Weaknesses:**
  - Requires manual scroll state management
  - No animation utilities
  - Must write custom trigger logic
- **Use Case Fit:** Lightweight option for simple scroll-step transitions; combines well with three.js animation loop

---

### Svelte-Native Approaches
- **Framework:** SvelteKit
- **Strengths:**
  - Svelte's reactive declarations (`$:`) simplify scroll-position binding
  - Motion stores (`tweened`, `spring`) provide smooth animations
  - No runtime overhead for scroll tracking
  - SSR-friendly (important for static export)
- **Weaknesses:**
  - Tightly coupled to Svelte; less portable
  - Still need IntersectionObserver or scroll event listener underneath
- **Use Case Fit:** Good if adopting SvelteKit; complements Scrollama

---

## 3. Terrain & Raster Tile Formats and Serverless Serving

### Terrarium / Terrain-RGB PNG Tiles
- **Format:** PNG, 16-bit integer + 8-bit fractional elevation per RGB channel
- **Origin:** Mapzen; now standard (GDAL support)
- **Serverless Serving:** Yes (static PNG tiles; HTTP range requests not needed)
- **Strengths:**
  - Simple format; easy to generate and understand
  - Supported by MapLibre GL, CesiumJS, three.js (via decoding)
  - Works in browser with minimal overhead
- **Weaknesses:**
  - Larger file size than quantized-mesh for same coverage
  - Loss of precision (24-bit total for 16-bit integer + 8-bit fraction)
- **Tools:** rio-rgbify (Python), GDAL, QGIS
- **Browser Rendering:** Decoding library needed (e.g., custom decoder or CPU-side)
- **Use Case Fit:** Good for coarse hillshade overlays or low-res elevation visualization

---

### Quantized-Mesh
- **Format:** Binary mesh (vertices, triangles) per tile
- **Standard:** OGC Community Standard (CesiumGS/quantized-mesh spec)
- **Serverless Serving:** Yes (static binary files)
- **Maturity:** Well-established; active 2026 development
- **Strengths:**
  - Compact binary format; efficient to stream
  - Native support in CesiumJS, AGI Cesium Components, deck.gl (WIP)
  - Good compression (similar to or better than Terrain-RGB PNG)
  - Natural mesh topology for GPU rendering
- **Weaknesses:**
  - Requires specialized tooling to generate (quantized-mesh-tile, GDAL)
  - Less universal browser support than Terrain-RGB
  - Specification complex; tools less mature than raster alternatives
- **Tools:** quantized-mesh-tile (Python), GDAL (recent support), Cesium tools
- **Browser Rendering:** Supported by CesiumJS; limited support in three.js (custom decoder needed)
- **Use Case Fit:** Excellent for CesiumJS; solid for quantized-mesh-aware engines; less ideal for three.js

---

### 3D Tiles (Cesium 3D Tiles)
- **Format:** Heterogeneous 3D content (meshes, point clouds, models)
- **Standard:** OGC Standard (1.1 approved 2022-12-17); supports glTF 2.0 as tile content
- **Serverless Serving:** Partially (requires HTTP range requests for scalability; S3 + CloudFront or similar)
- **Maturity:** Widely adopted in 2026; Google Photorealistic 3D Tiles, ArcGIS, deck.gl support
- **Strengths:**
  - Standard format for massive geospatial datasets
  - Excellent for photogrammetry, building models, point clouds
  - Wide tooling ecosystem (ArcGIS, GDAL, Cesium tools)
  - Scalable to terabytes of data
- **Weaknesses:**
  - Complex specification; steep learning curve
  - Generation tooling expensive or proprietary (Google, Esri)
  - Overkill for simple terrain + raster combinations
  - Requires tile server for efficient access (though CDN + range requests work)
- **Browser Support:** CesiumJS, deck.gl (Tile3DLayer), ArcGIS JS SDK
- **Use Case Fit:** Excellent for photorealistic geology or point-cloud visualization; overkill for DEM + raster overlay

---

### Cloud-Optimized GeoTIFF (COG)
- **Format:** GeoTIFF with internal tiling and overviews
- **Serverless Serving:** Yes (HTTP range requests fetch only required tiles)
- **Browser Rendering:** Via geotiff.js library
- **Strengths:**
  - Single-file distribution (no tiling infrastructure needed)
  - Excellent for satellite imagery, DEMs, time-series arrays
  - Native GDAL support
- **Weaknesses:**
  - geotiff.js decoder is CPU-bound; large arrays slow in browser
  - Not ideal for high-frequency tile access
  - File size grows with coverage; not as efficient as tiled schemes
- **Tools:** gdal_translate, rio-cogeo (rasterio), QGIS
- **Browser Rendering:** geotiff.js (JavaScript decoder; CPU-bound)
- **Use Case Fit:** Good for single, complete geological datasets; less ideal for multi-layer tiled visualization

---

### PMTiles
- **Format:** Single-file archive containing all tile pyramid (vector or raster)
- **Serverless Serving:** **Excellent** (HTTP range requests; no server needed)
- **Maturity:** Growing adoption; 2026 support in GDAL, MapLibre tools
- **Strengths:**
  - Single `.pmtiles` file (easy to host on S3, GitHub, any static storage)
  - Supports both raster and vector tiles
  - Efficient internal directory (Hilbert curve) for range requests
  - Zero tile server required
  - GDAL support for generation
- **Weaknesses:**
  - Newer format (less tooling maturity than individual tile sets)
  - Browser libraries still maturing
  - Single-file limitation if updates needed (must re-publish entire archive)
- **Tools:** PMTiles CLI, GDAL (gdal_translate), tippecanoe integration
- **Browser Support:** MapLibre GL, PMTiles.js (JavaScript client)
- **Use Case Fit:** **Ideal for static hosting** of terrain + raster overlay; excellent match for this project

---

### Zarr
- **Format:** Multidimensional array archive (time, lat, lon, depth, etc.)
- **Serverless Serving:** Yes (HTTP range requests; cloud-friendly)
- **Browser Rendering:** Via Browzarr or custom zarr.js decoders
- **Strengths:**
  - Excellent for time-series data (ice-model outputs)
  - Efficient subsetting by time/space
  - Native Python/xarray integration
  - Cloud-optimized storage (S3, GCS compatible)
- **Weaknesses:**
  - Browser decoding immature; complex for high-dimensional data
  - Visualizing 4D (time + space) data in browser non-trivial
  - JavaScript support emerging (not mature)
- **Tools:** xarray (Python), zarr.js (JavaScript, emerging), titiler (tiling server)
- **Browser Rendering:** Browzarr (visualization framework), custom zarr-gl approaches
- **Use Case Fit:** Good for ice-model time-series data backend; visualization layer (Zarr → raster tiles → MapLibre) needed

---

## 4. Data Pipeline Tooling

### GDAL
- **Latest Version:** 3.9+ (2026 releases)
- **License:** MIT
- **Maturity:** Industry standard; 30+ years of development
- **Strengths:**
  - Universal raster/vector geospatial translator
  - Supports all major formats (GeoTIFF, NetCDF, Zarr, PNG, quantized-mesh, PMTiles, etc.)
  - Command-line and C/C++/Python APIs
  - Cross-platform
- **Weaknesses:**
  - Steep learning curve (many options and formats)
  - Not optimized for web-scale tiling (see rio-tiler)
- **Docs:** https://gdal.org/ [from search]
- **Use Case Fit:** Essential for format conversion (DEM → tiles, NetCDF → raster)

---

### Rasterio
- **Latest Version:** 1.3+ (active 2026)
- **License:** MIT
- **Maturity:** Production-ready; widely adopted in geoscience
- **Strengths:**
  - Pythonic GDAL wrapper; much easier than raw GDAL
  - Reads/writes GeoTIFF, NetCDF, COG, and more
  - Array-like API (NumPy integration)
  - Cloud-native (S3, GCS support)
- **Weaknesses:**
  - Python-only (requires build server)
  - Slower than GDAL for large operations
- **Docs:** https://rasterio.readthedocs.io/ [from search]
- **Use Case Fit:** Ideal Python-based data preparation; convert DEM and geology rasters to tiles

---

### rio-tiler
- **Latest Version:** 6.x (2026)
- **License:** MIT
- **Maturity:** Production-ready; actively developed
- **Strengths:**
  - High-level tile generation API (reads from any rasterio-supported source)
  - Supports local files, S3, GCS, HTTP sources
  - Helper methods for metadata, statistics
  - Foundation for titiler (dynamic tile server)
- **Weaknesses:**
  - Dynamic tiling requires server (not serverless)
  - Pre-generated tiles (via cogeo-mosaic or rio-cogeo) still recommended
- **Docs:** https://cogeotiff.github.io/rio-tiler/latest/ [verified via search]
- **Use Case Fit:** Good for pre-generating Terrain-RGB or COG tiles from DEM + geology rasters

---

### rio-rgbify
- **Latest Version:** Not specified in search
- **License:** MIT
- **Maturity:** Mature plugin
- **Strengths:**
  - Encodes high bit-depth rasters (16-bit, 32-bit) into RGB PNG tiles
  - Essential for geology raster layers
  - Integrates with rasterio/GDAL pipeline
- **Weaknesses:**
  - Requires manual decoding in browser (or server-side generation)
  - Not widely documented outside rasterio ecosystem
- **Docs:** https://github.com/mapbox/rio-rgbify [from search]
- **Use Case Fit:** Excellent for encoding geological data into web-friendly tiles

---

### tippecanoe
- **Latest Version:** 1.36+ (2026)
- **License:** BSD
- **Maturity:** Production-ready; Mapbox-maintained
- **Strengths:**
  - Generates vector tiles (.mbtiles, .pmtiles) from GeoJSON, shapefiles, etc.
  - Excellent zoom-level control; automatic simplification
  - Fast and memory-efficient
- **Weaknesses:**
  - Vector-tile focused (not suitable for raster geology)
- **Docs:** https://github.com/mapbox/tippecanoe [from search]
- **Use Case Fit:** Good for vector tectonic plate boundaries or structure outlines

---

### PMTiles CLI
- **Latest Version:** 3+ (2026)
- **License:** MIT
- **Maturity:** Growing; modern tooling
- **Strengths:**
  - Generates .pmtiles archives directly
  - Serverless-friendly output format
  - Works with raster and vector tiles
- **Weaknesses:**
  - Newer tool; less mature than tiling alternatives
- **Use Case Fit:** **Highly recommended** for this project; creates single-file serverless distribution

---

### QGIS
- **Latest Version:** 3.36+ (2026)
- **License:** LGPL / open source
- **Maturity:** Very mature; standard in GIS
- **Strengths:**
  - Visual tool for raster/vector processing
  - Good for understanding data and QA/QC
  - Supports most formats and transformations
  - Plugin ecosystem (e.g., Mesh Terrain Generation)
- **Weaknesses:**
  - Manual tool (not automation-friendly for CI/CD)
  - Slower than CLI alternatives for batch processing
- **Use Case Fit:** Good for exploratory data preparation and QA; use CLI tools (rio-tiler, GDAL) for production

---

### pygplates / gplately
- **Latest Version:** gplately last released May 2026; pygplates also current
- **License:** LGPL (pygplates), MIT (gplately)
- **Maturity:** Production-ready; mature geoscience tools
- **Strengths:**
  - Only Python library for plate reconstruction
  - gplately high-level interface (tracks plate positions over time)
  - Can reconstruct rasters, vectors through deep geologic time
  - Active community (EarthByte lab, Sydney)
- **Weaknesses:**
  - Python-only (requires offline computation)
  - Output still requires conversion to web-friendly formats
  - Plate model selection critical and model-dependent
- **Docs:** 
  - pygplates: https://www.earthbyte.org/category/resources/software-workflows/pygplates/ [from search]
  - gplately: https://github.com/GPlates/gplately [verified via search]
- **Use Case Fit:** Essential for Triassic reef-platform paleogeography and plate boundary animation

---

### xarray
- **Latest Version:** 2024+ (active 2026 development)
- **License:** Apache 2.0
- **Maturity:** Production-ready; standard in climate/oceanography
- **Strengths:**
  - Native NetCDF/Zarr I/O
  - Time-series data handling (CF conventions)
  - NumPy-like API for multidimensional arrays
  - Works with ice-model output
- **Weaknesses:**
  - Python-only (offline analysis)
  - In-browser time-series visualization requires export to tiles/raster
- **Docs:** https://docs.xarray.dev/ [from search]
- **Use Case Fit:** **Essential** for processing LGM ice-model NetCDF time series → raster tiles

---

## 5. Site Frameworks (Static / Multilingual)

### Astro
- **Latest Version:** 4.x (2026 releases; native i18n routing in 3.0+)
- **License:** MIT
- **Bundle Size:** Zero JS by default (static HTML output); opt-in JS per component
- **Maturity:** Mature; rapidly growing adoption (especially 2024–2026)
- **Strengths:**
  - **First-class i18n routing** (native in Astro 4.0)
  - Zero JavaScript default; content ships as plain HTML (fast)
  - File-based routing; integrates i18n naturally (`/de/`, `/it/`, `/en/`, `/ladin/`)
  - Content Collections (good for multilingual content management)
  - Built-in partial prerendering (static HTML + dynamic endpoints)
  - Excellent Lighthouse scores out of the box
- **Weaknesses:**
  - Younger ecosystem (less third-party plugins than Next.js)
  - Overkill if not using markdown/content-driven approach
  - Island architecture (client components) less familiar to some devs
- **i18n Pattern:** Default locale without prefix (`/about`), other locales with prefix (`/de/about`)
- **Docs:** https://astro.build/ [from search]
- **Use Case Fit:** **Excellent choice** for static multilingual site; zero-JS default speeds loading

---

### SvelteKit
- **Latest Version:** 2.x (2026)
- **License:** MIT
- **Bundle Size:** Zero JS by default (with static adapter); per-component opt-in
- **Maturity:** Stable; production-ready since 2021
- **Strengths:**
  - `@sveltejs/adapter-static` for static export; full control over prerendering
  - Svelte's compiler-driven reactivity (smallest JavaScript)
  - Built-in i18n via stores and route parameters
  - SSR-friendly; can be used as static site generator
- **Weaknesses:**
  - No first-class i18n routing (manual route structure needed)
  - Smaller ecosystem than Next.js or Astro
  - Requires understanding of Svelte's reactivity model
- **i18n Pattern:** Manual routes (`src/routes/[lang]/` with dynamic param or hook-based)
- **Docs:** https://kit.svelte.dev/docs/adapter-static [verified 2026-09-06]
- **Use Case Fit:** Good choice if Svelte is preferred; requires more i18n boilerplate than Astro

---

### Next.js (Static Export)
- **Latest Version:** 15+ (2026 releases)
- **License:** MIT
- **Bundle Size:** 0 JS (static export); configurable hydration
- **Maturity:** Mature; most popular React framework
- **Strengths:**
  - `output: 'export'` for static site generation
  - Excellent React ecosystem
  - App Router (Layouts, error boundaries, etc.) available for static
  - `generateStaticParams()` for dynamic routes
- **Weaknesses:**
  - i18n requires manual setup or third-party library (next-intl, next-i18next)
  - No first-class i18n routing (unlike Astro or SvelteKit)
  - Overkill footprint for static-only sites
  - Build complexity compared to Astro
- **i18n Pattern:** Manual implementation via next-intl or middleware; usually `/[locale]/...`
- **Docs:** https://nextjs.org/docs/app/guides/static-exports [verified 2026-09-06]
- **Use Case Fit:** Solid fallback if Next.js expertise exists; requires i18n library; Astro is better fit

---

### Vite
- **Latest Version:** 5.x (2026)
- **License:** MIT
- **Bundle Size:** 0 (static build only)
- **Maturity:** Mature build tool; increasingly used as static site generator
- **Strengths:**
  - Lightning-fast dev server and builds
  - Minimal configuration; tree-shakes unused code
  - Works with any framework (Vue, React, Svelte, vanilla JS)
  - Excellent for custom static pipelines
- **Weaknesses:**
  - No framework-level i18n support (must build custom)
  - Less convention-driven than Astro or Next.js (more boilerplate)
  - Smaller ecosystem for static sites
- **i18n Pattern:** Manual routing and build scripting; `vite-plugin-i18n` or custom
- **Docs:** https://vitejs.dev/ [from search]
- **Use Case Fit:** Good foundation if custom architecture needed; requires more work than Astro

---

### i18n for DE/IT/EN/Ladin
| Framework | Approach | Ease | Notes |
|-----------|----------|------|-------|
| **Astro** | Native i18n routing | Easy | First-class support; `/de/`, `/it/`, `/en/`, `/ladin/` |
| **SvelteKit** | Manual routes + stores | Medium | Functional but requires boilerplate |
| **Next.js** | next-intl or middleware | Medium | Requires external library; well-documented |
| **Vite** | Custom + i18n plugin | Hard | Flexible but low-level; significant setup |

**Recommendation:** Astro has the best native support for this use case.

---

## 6. Hosting (Static)

### GitHub Pages
- **Repository Size Limit:** 1 GB (soft; rarely enforced for public repos)
- **Bandwidth:** 100 GB/month soft limit (rarely enforced; intended for personal/open-source use)
- **File Size Limit:** Per-file limit not specified; practical limit ~1 GB
- **Pricing:** Free
- **Build:** GitHub Actions (free minutes; adequate for static sites)
- **HTTPS:** Automatic (enforced for custom domains)
- **Strengths:**
  - Zero cost; integrated with GitHub repo
  - Reliable; backed by GitHub infrastructure
  - Simple deployment (push to branch)
- **Weaknesses:**
  - Bandwidth limits are soft; business use at risk
  - Limited to GitHub infrastructure location
  - No real-time analytics or caching control
- **Use Case Fit:** Good for open-source or non-commercial projects; risky for high-traffic sites

---

### Cloudflare Pages
- **File Count Limit:** 20,000 files (free tier)
- **Max File Size:** 25 MB per file
- **Bandwidth:** Unlimited (free tier)
- **Pricing:** Free tier; $20+/month for Teams
- **Build:** Cloudflare Build (automatic from Git; 500 builds/month free)
- **HTTPS:** Automatic
- **Strengths:**
  - **Unlimited bandwidth** (huge advantage for this use case)
  - Global CDN (fast worldwide delivery)
  - Real-time logs and caching control
  - 25 MB per-file limit accommodates large tiles
  - Zero build minutes (unlike Vercel/Netlify)
- **Weaknesses:**
  - 20,000 file limit (challenging if many small tile files; PMTiles solves this)
  - Fewer integrations than Netlify/Vercel
  - Cold start on edge functions (if used)
- **Use Case Fit:** **Excellent choice** for serverless terrain tiles; unlimited bandwidth is critical

---

### Netlify
- **File Count Limit:** Unlimited
- **Bandwidth:** Credit-based (April 2026 change): Free = 300 credits/month; Pro = 3,000 credits; 20 credits/GB bandwidth
- **Pricing:** Free tier (300 credits = 15 GB bandwidth); Pro $20/month (150 GB); Enterprise custom
- **Build:** Netlify CI (300 free minutes/month)
- **HTTPS:** Automatic
- **Strengths:**
  - Large ecosystem (integrations, CMS support, edge functions)
  - Simple deployment
  - Good UI/UX
- **Weaknesses:**
  - Bandwidth credit system penalizes high-traffic data sites
  - April 2026 pricing change reduced free bandwidth from 100 GB to 15 GB (300 credits)
  - More expensive than alternatives for tile-heavy sites
- **Use Case Fit:** Not ideal; bandwidth credit model is expensive for large raster tile serving

---

### Vercel
- **File Count Limit:** 12,500 source files; 16,000 build output files
- **Bandwidth:** 100 GB/month (free tier)
- **Pricing:** Free (100 GB bandwidth); Pro $20/month (1 TB); Enterprise custom
- **Build:** Vercel CI (5 free deployments/day; unlimited per month)
- **HTTPS:** Automatic
- **Strengths:**
  - Excellent Next.js integration
  - Global CDN; very fast worldwide
  - Good developer experience
- **Weaknesses:**
  - Bandwidth cap at 100 GB free (same as GitHub Pages, but enforced)
  - Function-focused (not ideal for static-only sites)
  - Similar pricing pressure as Netlify
- **Use Case Fit:** Acceptable but not optimal; bandwidth limit is restrictive for tile-heavy sites

---

### Hosting Comparison Summary
| Platform | Bandwidth | Files | Cost | CDN | Best For |
|----------|-----------|-------|------|-----|----------|
| **GitHub Pages** | 100 GB (soft) | 1 GB repo | Free | GitHub | OSS; low traffic |
| **Cloudflare Pages** | **Unlimited** | 20K (PMTiles workaround) | Free | Excellent | **Recommended** |
| **Netlify** | 15 GB free (300 credits) | Unlimited | $20 Pro | Good | High-traffic dynamic; no tiles |
| **Vercel** | 100 GB | 16K | Free | Excellent | Next.js; not tile-heavy |

**Recommendation:** **Cloudflare Pages** with PMTiles (single-file archive) is ideal; unlimited bandwidth removes bottleneck.

---

## Candidate Stacks

### Option A: MapLibre + PMTiles + Astro (Recommended)
**Stack:**
- **3D Rendering:** MapLibre GL JS (2.5D terrain) + three.js (custom 3D overlays for plate/ice visualization)
- **Scrollytelling:** Scrollama + GSAP ScrollTrigger
- **Tiles:** PMTiles (raster terrain + geology overlays)
- **Data Pipeline:** GDAL / rasterio / rio-rgbify (terrain + geology rasters) → PMTiles CLI
- **Plate Recons:** pygplates / gplately (Triassic paleogeography) → raster export → tiles
- **Ice Model:** xarray (ice-thickness NetCDF) → raster tiles → PMTiles
- **Framework:** Astro (native i18n for DE/IT/EN/Ladin)
- **Hosting:** Cloudflare Pages

**Strengths:**
- Minimal JavaScript (Astro zero-JS default); very fast initial load
- PMTiles serverless distribution (single file, no tile server needed)
- Unlimited Cloudflare bandwidth (critical for global terrain/tile serving)
- MapLibre 2.5D terrain is simple, fast, proven
- three.js adds flexibility for custom 3D animations (plate tectonics, ice sheet overlay)
- Native Astro i18n simplifies multilingual setup
- Well-established tool chain (GDAL, pygplates, xarray mature)

**Weaknesses:**
- MapLibre terrain is 2.5D only (not true 3D volumetric)
- Requires custom three.js code to sync scrolling with 3D animations
- Platform reconstructions require offline processing (pygplates)
- Ice model time-series requires rasterization at multiple time steps (generates many tiles)

**Tile Count Estimate:** ~5,000–10,000 raster tiles (multiple zoom levels, layers) → fits in PMTiles single file (~100–500 MB)

---

### Option B: CesiumJS + Static Hosting + Next.js Static Export
**Stack:**
- **3D Rendering:** CesiumJS (time-dynamic support built-in; CZML)
- **Scrollytelling:** Scrollama (synchronize scroll to Cesium viewer state)
- **Tiles:** CesiumJS terrain provider (quantized-mesh or Terrarium PNG); 3D Tiles for photorealistic geology (if available)
- **Data Pipeline:** GDAL / quantized-mesh-tile (DEM) + rio-rgbify (geology rasters)
- **Plate Recons:** pygplates → CZML generation (animated plate positions over time)
- **Ice Model:** xarray → CZML or raster → terrain provider
- **Framework:** Next.js static export (or Astro with similar setup)
- **Hosting:** Cloudflare Pages or GitHub Pages (tile server needed for dynamic CZML; alternative: pre-generate all states)

**Strengths:**
- CesiumJS has first-class CZML support for time-dynamic scenes (ideal for plate tectonics animation)
- True 3D globe (not 2.5D)
- Built-in time controls and animation UI
- Excellent for complex geological narratives
- Large community and documentation

**Weaknesses:**
- CesiumJS large library footprint (slower initial load than MapLibre + three.js)
- Cesium Ion pricing ($149+/month) if custom terrain/imagery used (can be avoided with self-hosted providers)
- CZML generation from pygplates output requires custom scripting
- Scrollama + Cesium synchronization is manual and complex
- CesiumJS not designed for minimal-footprint static hosting

**Tile Count Estimate:** ~3,000–5,000 terrain + imagery tiles; CZML data for plate positions (can be baked into HTML)

---

### Option C: three.js + Custom Terrain Morphing + SvelteKit Static Export
**Stack:**
- **3D Rendering:** three.js (custom terrain mesh from DEM tiles; vertex-shader morphing between elevation states)
- **Scrollytelling:** Scrollama + custom three.js animation loop (tight scroll-to-3D sync)
- **Tiles:** PMTiles or COG (elevation data); rio-rgbify tiles (geology rasters)
- **Data Pipeline:** GDAL / rasterio / rio-tiler (DEM + geology rasters → PNG tiles + PMTiles)
- **Plate Recons:** pygplates → raster overlays (plate boundaries rendered as textures or lines)
- **Ice Model:** xarray → time-stepped terrain elevation grids (morph between time steps)
- **Framework:** SvelteKit (static adapter; Svelte reactivity simplifies scroll-to-render binding)
- **Hosting:** Cloudflare Pages (PMTiles) or GitHub Pages

**Strengths:**
- Minimal bundle size (three.js ~155 KB gzipped; smallest option)
- Full control over terrain mesh and morphing (can do sophisticated animations)
- Svelte reactivity makes scroll-to-animation binding elegant
- Excellent for performance-critical sites
- Custom WebGPU shaders possible (with three.js r171+)

**Weaknesses:**
- Steep development effort (must write custom terrain morphing, layer compositing)
- Limited ecosystem support for time-dynamic visualization (more boilerplate)
- No built-in globe projection (can be added with custom shaders, but non-trivial)
- Smaller community; fewer examples for geological use cases

**Tile Count Estimate:** ~5,000–10,000 raster tiles (same as Option A)

---

## Decision Criteria

| Criterion | Option A | Option B | Option C |
|-----------|----------|----------|----------|
| **Initial Load Speed** | Fast (Astro zero-JS) | Slow (CesiumJS large) | Fast (three.js minimal) |
| **3D Capability** | 2.5D only | True 3D + time-dynamic | True 3D + custom morphing |
| **Time Series (Plates, Ice)** | Raster overlay only | CZML + native support | Custom mesh morphing |
| **i18n Ease** | Best (Astro native) | Medium (manual) | Medium (manual) |
| **Hosting Simplicity** | Excellent (PMTiles serverless) | Good (tile provider URL) | Excellent (PMTiles serverless) |
| **Development Time** | Medium (established patterns) | Medium-High (CZML scripting) | High (custom terrain code) |
| **Bandwidth Cost** | Low (Cloudflare unlimited) | Medium (tile server or baked CZML) | Low (Cloudflare unlimited) |
| **Scalability** | High (static + CDN) | Medium (depends on Cesium Ion) | High (static + CDN) |
| **Community / Docs** | Good | Excellent | Medium |

---

## Recommendations

### **Primary Recommendation: Option A** (MapLibre + PMTiles + Astro + Cloudflare Pages)
**Why:** Best balance of ease, speed, cost, and multimodal content for this use case. Native Astro i18n solves multilingual complexity. Cloudflare unlimited bandwidth removes a hard constraint. PMTiles serverless distribution is elegant. MapLibre 2.5D terrain sufficient for DEM + geology visualization; three.js layer adds flexibility for custom 3D elements without bloat.

### **Alternative if Rich Time-Dynamic Animation Required: Option B** (CesiumJS)
**Why:** If the core narrative centers on animated plate tectonics or ice-sheet evolution, CesiumJS's CZML support and built-in animation UI justify the larger footprint. Trade speed for animation sophistication. Requires careful planning to avoid Cesium Ion pricing lock-in.

### **Alternative if Minimal Footprint Critical: Option C** (three.js + SvelteKit)
**Why:** If performance is paramount (e.g., mobile-first design, slow networks), three.js + SvelteKit offers smallest bundle and full control. Requires strong frontend development (custom shaders, terrain morphing). Best for teams experienced with Three.js.

---

## Sources

### Search / Fetch References
- [CesiumJS](https://cesium.com/platform/cesiumjs/) [verified 2026-09-06]
- [deck.gl](https://deck.gl/) [verified 2026-09-06]
- [three.js](https://threejs.org/) [verified 2026-09-06]
- [MapLibre GL JS](https://maplibre.org/maplibre-gl-js/) [verified 2026-09-06]
- [Babylon.js](https://doc.babylonjs.com/) [verified via search]
- [Globe.gl](https://globe.gl/) [verified 2026-09-06]
- [procedural-gl.js](https://www.procedural.eu/) [verified 2026-09-06]
- [OpenLayers](https://openlayers.org/) [verified 2026-09-06]
- [Scrollama](https://github.com/russellsamora/scrollama) [verified via search]
- [GSAP](https://gsap.com/) [verified 2026-09-06]
- [PMTiles](https://github.com/protomaps/pmtiles) [verified via search]
- [rasterio](https://rasterio.readthedocs.io/) [verified via search]
- [rio-tiler](https://cogeotiff.github.io/rio-tiler/latest/) [verified via search]
- [pygplates](https://www.earthbyte.org/category/resources/software-workflows/pygplates/) [verified via search]
- [gplately](https://github.com/GPlates/gplately) [verified via search]
- [xarray](https://docs.xarray.dev/) [verified via search]
- [Astro](https://astro.build/) [verified via search]
- [SvelteKit Static Adapter](https://kit.svelte.dev/docs/adapter-static) [verified 2026-09-06]
- [Next.js Static Export](https://nextjs.org/docs/app/guides/static-exports) [verified 2026-09-06]
- [Cloudflare Pages](https://pages.cloudflare.com/) [from search]
- [GitHub Pages](https://pages.github.com/) [from search]
- [Netlify](https://www.netlify.com/) [from search]
- [Vercel](https://vercel.com/) [from search]
