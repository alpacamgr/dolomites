# Data

## Layout

- `manifests/` - one YAML per dataset (committed). The manifest is the record of where a dataset came from and what we did to it.
- `scripts/` - download and processing scripts (committed). Re-running them regenerates `raw/` and `processed/`.
- `raw/` - original files exactly as downloaded (git-ignored). Never edited in place.
- `processed/` - tiles, meshes, JSON, and other derived files the app consumes (git-ignored). Always rebuildable from `raw/` plus `scripts/`.

## Adding a dataset

1. Copy `manifests/TEMPLATE.yaml` to `manifests/<dataset-id>.yaml` and fill it in. The `id` becomes the folder name under `raw/` and `processed/`.
2. Write or extend a script in `scripts/` that downloads into `raw/<dataset-id>/` and records the checksum.
3. Confirm the license allows our use (web display, derivative tiles) and record the required attribution string.
4. Only then process into `processed/<dataset-id>/`.

## Dataset id convention

`<provider>-<product>-<version-or-year>`, lowercase, hyphenated. Examples: `bz-dtm-2p5m-2006`, `earthbyte-muller2019`, `seguinot2018-alps-1km`.
