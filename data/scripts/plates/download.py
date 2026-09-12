"""Download the plate model used by the globe pipeline.

Pulls the Scotese and Wright 2018 / PALEOMAP plate model (gplately
PlateModelManager name ``scotese_and_wright2018``) into
``data/raw/scotese-wright-2018-model/``. This is the reference frame in
which the PaleoDEM textures were built (ADR 0005), so it is the only model
the globe uses, for 0-300 Ma.

The script is idempotent: if the layer files already exist on disk,
PlateModelManager reuses them and no layer is re-downloaded. Re-running
only recomputes the SHA-256 index in
``data/raw/scotese-wright-2018-model/checksums.txt``.

Note: in this model the StaticPolygons, ContinentalPolygons and COBs layers
are the same file (Scotese_Wright_ContinentalPolygons.gpml) and there is no
Coastlines layer.
"""
from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RAW = REPO / "data" / "raw"

MODELS = {
    "scotese-wright-2018-model": "scotese_and_wright2018",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_one(dataset_id: str, pmm_name: str) -> dict:
    from gplately import PlateModelManager

    out = RAW / dataset_id
    out.mkdir(parents=True, exist_ok=True)
    pm = PlateModelManager()
    model = pm.get_model(pmm_name, data_dir=str(out))

    layers = {
        "rotation": model.get_rotation_model(),
    }
    for layer in ("StaticPolygons", "Topologies", "ContinentalPolygons",
                  "COBs"):
        try:
            files = model.get_layer(layer)
        except Exception as exc:  # pragma: no cover - depends on remote data
            files = None
            print(f"[{dataset_id}] {layer}: NOT AVAILABLE ({exc})")
        if files:
            layers[layer] = files

    all_files = []
    for names in layers.values():
        for f in names:
            all_files.append(Path(f).resolve())

    checks = []
    for f in sorted(set(all_files)):
        if not f.exists():
            continue
        digest = sha256(f)
        rel = f.relative_to(out.resolve())
        checks.append(f"{digest}  {rel.as_posix()}")

    (out / "checksums.txt").write_text("\n".join(checks) + "\n",
                                       encoding="utf-8")

    return {
        "dataset_id": dataset_id,
        "pmm_name": pmm_name,
        "layers": {k: [str(Path(p)) for p in v] for k, v in layers.items()},
        "num_files": len(checks),
    }


def main() -> int:
    for _ in range(3):
        try:
            for dsid, name in MODELS.items():
                info = download_one(dsid, name)
                print(f"[{dsid}] ready. files={info['num_files']}")
            return 0
        except OSError as exc:
            if "being used" in str(exc) or "WinError 32" in str(exc):
                print(f"file lock: retrying in 20s ({exc})", file=sys.stderr)
                time.sleep(20)
                continue
            raise
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
