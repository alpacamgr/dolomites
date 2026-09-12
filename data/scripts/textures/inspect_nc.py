"""Inspect one PaleoDEM NetCDF and the ETOPO NetCDF to document conventions.

Reports variable names, dtype, shape, units, lon/lat range and ordering, sign
convention, nodata handling, and a small stats summary. Prints as JSON so the
render script can pick it up.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[3]
PALEO_NC_DIR = ROOT / "data" / "raw" / "scotese-paleodem-2018-v2" / "nc"
ETOPO_NC = ROOT / "data" / "raw" / "noaa-etopo2022-60s" / "ETOPO_2022_v1_60s_N90W180_surface.nc"


def summarise(ds: xr.Dataset, name: str) -> dict:
    info: dict = {"file": name, "variables": {}, "dims": dict(ds.sizes)}
    for v in ds.data_vars:
        arr = ds[v]
        info["variables"][v] = {
            "dtype": str(arr.dtype),
            "shape": list(arr.shape),
            "attrs": {k: (str(val)[:120]) for k, val in arr.attrs.items()},
        }
    for c in ds.coords:
        arr = ds.coords[c]
        info["variables"][c] = {
            "dtype": str(arr.dtype),
            "shape": list(arr.shape),
            "attrs": {k: (str(val)[:120]) for k, val in arr.attrs.items()},
            "min": float(np.nanmin(arr.values)),
            "max": float(np.nanmax(arr.values)),
            "monotonic": (
                "asc" if np.all(np.diff(arr.values) > 0)
                else "desc" if np.all(np.diff(arr.values) < 0)
                else "mixed"
            ),
        }
    # elevation stats: pick first data var
    for v in ds.data_vars:
        arr = ds[v].values.astype("float64")
        finite = np.isfinite(arr)
        info["elevation_stats"] = {
            "variable": v,
            "min_m": float(arr[finite].min()) if finite.any() else None,
            "max_m": float(arr[finite].max()) if finite.any() else None,
            "mean_m": float(arr[finite].mean()) if finite.any() else None,
            "nan_frac": float((~finite).mean()),
            "below_zero_frac": float((arr[finite] < 0).mean()) if finite.any() else None,
        }
        break
    return info


def main() -> int:
    out: dict = {}
    ncs = sorted(PALEO_NC_DIR.glob("*.nc")) if PALEO_NC_DIR.exists() else []
    print(f"Found {len(ncs)} paleo netCDFs in {PALEO_NC_DIR}")
    if ncs:
        with xr.open_dataset(ncs[0]) as ds:
            out["paleo_sample"] = summarise(ds, ncs[0].name)
        # summarise variable name variety across files
        names = set()
        for p in ncs[:5]:
            with xr.open_dataset(p) as ds:
                names.update(ds.data_vars)
        out["paleo_varnames_first5"] = sorted(names)
        out["paleo_file_names"] = [p.name for p in ncs]

    if ETOPO_NC.exists():
        with xr.open_dataset(ETOPO_NC) as ds:
            out["etopo"] = summarise(ds, ETOPO_NC.name)

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
