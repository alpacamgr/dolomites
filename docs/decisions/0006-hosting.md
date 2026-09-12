# 0006 - Hosting: everything static on Cloudflare Pages, map tiles as individual files

Date: 2026-09-12 - Status: accepted; amended 2026-09-12 (served as Cloudflare Workers static assets, see Amendment)

## Context

The first production build was 458 MB, almost all of it data. Two single files exceeded common static-host limits: the terrain archive (PMTiles, about 310 MB) and the merged geology archive (PMTiles, about 61 MB). The site must load fast and never lag.

Checked on 2026-09-12:

| Item | Value | Source |
|---|---|---|
| Cloudflare Pages, maximum size of one asset | 25 MiB | developers.cloudflare.com/pages/platform/limits/ |
| Cloudflare Pages, files per site | 20,000 (free), 100,000 (paid) | same page |
| Cloudflare R2 egress | free; storage $0.015 per GB-month, 10 GB free | developers.cloudflare.com/r2/pricing/ |
| PMTiles on R2 | needs a Worker on an own domain for CORS and edge caching; Protomaps warns R2 latency can be 500 ms or higher | docs.protomaps.com/deploy/cloudflare |
| Terrain tiles | 958 tiles, mean 316 KB, max 460 KB | measured from the archive |
| Geology tiles | 2,070 tiles, mean 29 KB, max 989 KB | measured from the archive |
| Other data files | 753 (textures, plate JSON, ice frames, vectors, curves) | counted |

Two encoding options for terrain tiles were measured on 60 random tiles:

| Encoding | Size vs PNG | Change to heights |
|---|---|---|
| Lossless WebP, 0.1 m (as today) | 0.687 | none, bit-identical round trip |
| Lossless WebP, heights rounded to 1 m | 0.420 | up to 0.5 m; visible terracing in hillshade on flat valley floors (compare `data/processed/terrain/preview/quantization-hillshade.png`: 0.1 m, 0.5 m, 1 m) |

## Decision

1. **Everything is served from Cloudflare Pages as static files.** About 3,800 data files plus the site, far below the 20,000-file limit, with no file near 25 MiB.
2. **Map tiles are exported from the PMTiles build artifacts into `{z}/{x}/{y}` files**, each tileset described by a TileJSON file that MapLibre reads directly. PMTiles archives stay as pipeline intermediates in `data/processed/` and are no longer shipped. This avoids a Worker, avoids R2 latency, and lets the CDN cache every tile at the edge.
3. **Terrain tiles use lossless WebP at the source precision of 0.1 m** (about 31 % fewer bytes per tile than PNG, no change to any height). Rounding heights was rejected because it creates visible terracing.
4. R2 plus the PMTiles Worker stays documented as the fallback if a future dataset outgrows the Pages limits.

## Consequences

- Data contract sections 2.1 and 2.2 change to the served tile layout (see docs/04-data-contracts.md).
- The terrain pipeline gains an export step; the terrain engine switches its raster-dem and vector sources from `pmtiles://` to TileJSON URLs. Dev and production use the same layout.
- Build output drops by roughly the size of both archives minus the exported tiles (terrain tiles shrink by about a third through WebP).

## Amendment 2026-09-12: Workers static assets instead of Pages

The owner connected the GitHub repository github.com/alpacamgr/dolomites to Cloudflare through Workers Builds, Cloudflare's current path for static sites. The decision above is unchanged in substance; only the product differs.

Checked on 2026-09-12:

| Item | Value | Source |
|---|---|---|
| Workers static assets, files per Worker version | 20,000 (free), 100,000 (paid) | developers.cloudflare.com/workers/platform/limits/ |
| Workers static assets, maximum size of one asset | 25 MiB; no total size limit stated | same page |
| `_headers` file in the assets directory | supported, up to 100 rules | developers.cloudflare.com/workers/static-assets/headers/ |
| Assets-only Worker | `main` optional; `compatibility_date` required | developers.cloudflare.com/workers/wrangler/configuration/ |
| Workers Builds | build command optional, deploy command `npx wrangler deploy`; dashboard Worker name must equal `name` in the Wrangler file; 20 minute build limit | developers.cloudflare.com/workers/ci-cd/builds/ |
| Build image Node.js | from `.nvmrc` / `.node-version`, else `NODE_VERSION`, default 24.18.0 | developers.cloudflare.com/workers/ci-cd/builds/build-image/ |

Configuration in the repository: `wrangler.jsonc` (assets-only, directory `./app/dist`) and `.node-version` (24). Dashboard settings: build command `npm ci --prefix app && npm run build --prefix app`, deploy command `npx wrangler deploy`, root directory `/`. Only served data (`app/public/data`) is committed; `data/raw` and `data/processed` stay out of git and are reproduced from the manifests and pipeline scripts.
