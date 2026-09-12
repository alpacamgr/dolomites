# Dolomites Deep Time

An interactive, scroll-driven website that shows how the Dolomites (South Tyrol / Trentino / Belluno, Italy) came to be: the Permian volcanoes, the Triassic tropical sea and its reef platforms, the burial under later sediments, the collision of Adria with Europe, the rise of the Alps, and the ice ages that carved the valleys.

**Guiding rule:** nothing on screen is invented. Every map, number, and shape traces back to a published dataset or paper, and the interface labels each element as *observed*, *modeled*, *interpreted*, or *illustrative*. See [docs/03-data-policy.md](docs/03-data-policy.md).

## Status

**v0.1 runs end to end** (2026-09-12): a scroll-driven site in German, Italian and English with a whole-Earth globe for 300 million years of plate motion and a high-resolution terrain view of the Dolomites for the reefs, uplift, ice ages and today. Every layer carries an honesty label and a citation. Source: github.com/alpacamgr/dolomites; hosted as Cloudflare Workers static assets (ADR 0006).

Read first: [docs/00-vision.md](docs/00-vision.md), [docs/01-feasibility.md](docs/01-feasibility.md), [docs/02-architecture.md](docs/02-architecture.md), [docs/03-data-policy.md](docs/03-data-policy.md), [docs/04-data-contracts.md](docs/04-data-contracts.md) and the decisions in [docs/decisions/](docs/decisions/).

### Run it

```bash
npm --prefix app install
npm --prefix app run dev -- --port 4332
```

Open http://localhost:4332/en/ (also `/de/`, `/it/`). Engine test benches: `/en/dev/globe`, `/en/dev/terrain` (dev only, stripped from builds). The dev server does not watch `app/public/data`; restart it after regenerating data.

```bash
npm --prefix app run build
npm --prefix app run preview -- --port 4331
```

Visual QA in headless Chrome (works while the in-app browser is hidden):

```bash
node tools/qa/screenshot-chapters.mjs --base http://localhost:4331 --lang en --out qa-shots
```

### Deploy

The site is fully static and served as Cloudflare Workers static assets (no Worker script), configured in `wrangler.jsonc` with the Node version in `.node-version`; see [docs/decisions/0006-hosting.md](docs/decisions/0006-hosting.md). Cloudflare Workers Builds deploys every push to `main` with these dashboard settings:

| Setting | Value |
|---|---|
| Repository | `alpacamgr/dolomites`, production branch `main`, root directory `/` |
| Build command | `npm ci --prefix app && npm run build --prefix app` |
| Deploy command | `npx wrangler deploy` |
| Non-production branch deploy command | `npx wrangler versions upload` |

The Worker name in the dashboard must stay `dolomites`, matching `wrangler.jsonc`. The served data in `app/public/data` is committed (about 400 MB, no file over 25 MiB); raw downloads and intermediates are not.

### Data pipeline

Python 3.13 virtual environment in `.venv` (pygplates, gplately, rasterio, xarray, pmtiles). Each pipeline has a README: `data/scripts/plates/`, `data/scripts/textures/`, `data/scripts/terrain/`, `data/scripts/quaternary/`, `data/scripts/content/`. Raw downloads live in `data/raw/` and intermediates in `data/processed/` (both git-ignored); every dataset has a manifest in `data/manifests/`, summarised in [research/sources/license-register.md](research/sources/license-register.md).

### Known limits

- Plate positions and paleogeography are modelled at continental scale; the site shows no local paleo-elevation of the Dolomites because no such data exists.
- Six narrative facts are still marked *verification pending*; the site flags them.
- Rock colours come from six open geological maps at very different scales: South Tyrol and Trentino 1:10,000-1:25,000, swisstopo GeoCover 1:25,000, Veneto 1:250,000, and, where no provincial map is open, the older ISPRA 1:100,000 national map and GeoSphere Austria 1:500,000. About 0.5 % of the terrain area has no open geological map (hatched). Units whose age is missing or not trustworthy enough (for example ISPRA units whose stated age is a metamorphic age or contradicts their description) are drawn light grey, not coloured. The age mapping for the gap-fill sources awaits review by a geologist; judgement calls are listed in `data/scripts/terrain/geology_age_mapping.json` and the geology meta.

## Folder layout

```
Dolomites/
|-- README.md               this file
|-- docs/                   project documentation (vision, feasibility, architecture, policies)
|   `-- decisions/          architecture decision records (ADRs), one file per decision
|-- research/               sourced research notes; every claim carries a citation and a verification tag
|   |-- geology/            geological history of the Dolomites, stratigraphy, key papers
|   |-- tectonics/          plate reconstruction models and paleogeography datasets
|   |-- elevation/          present-day DEMs, imagery, geological and tectonic maps
|   |-- glaciation/         Quaternary ice, glaciers, uplift rates, climate and sea-level curves
|   |-- prior-art/          existing visualizations and what to learn from them
|   |-- tech/               rendering, tiling, scrollytelling, hosting options
|   `-- sources/            master bibliography and license register
|-- data/                   datasets
|   |-- manifests/          one YAML per dataset: origin, license, checksum, download date (committed)
|   |-- scripts/            reproducible download and processing scripts (committed)
|   |-- raw/                original downloads, untouched (git-ignored)
|   `-- processed/          derived tiles, meshes, JSON (git-ignored, rebuildable from scripts)
|-- assets/                 media used by the site
|   |-- images/             photos and figures with license notes alongside each file
|   |-- figures-redrawn/    our own redrawings of published figures, each citing the original
|   `-- icons/
|-- content/                editorial content, separate from code
|   |-- timeline/           timeline events as structured data (YAML), each with sources
|   `-- narrative/          scrollytelling chapter text, one folder per language
|-- app/                    the website: Astro + Svelte shell, three.js globe, MapLibre terrain; data under app/public/data
`-- tools/                  QA screenshots (tools/qa) and the license-register generator
```

## Conventions

- Dates are ISO 8601. Geological ages are in Ma (million years before present) using the ICS chart version named in `research/sources/`.
- Coordinates are WGS84 (EPSG:4326) unless a manifest says otherwise.
- Languages: German, Italian, and English content live side by side under `content/narrative/<lang>/`. Ladin is a goal, not a commitment yet.
- Nothing under `data/raw/` or `data/processed/` is committed. Manifests and scripts are, so the data can be rebuilt.
