"""Download source rasters for the globe textures.

- Scotese & Wright 2018 PaleoDEM 0.1 deg (~6 arc-min) NetCDF, Zenodo 5460860.
- NOAA ETOPO 2022 60 arc-second, ice-surface NetCDF.

Idempotent: skips files already present with the expected size, and re-verifies
MD5/SHA-256. Safe to run again after a partial download; uses HTTP Range to
resume. Writes real checksums into a small JSON sidecar under each raw dir so
the manifest writer can pick them up.
"""
from __future__ import annotations
import hashlib, json, os, sys, time, zipfile
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[3]  # E:/Projects/Dolomites
RAW = ROOT / "data" / "raw"
PALEO_DIR = RAW / "scotese-paleodem-2018-v2"
ETOPO_DIR = RAW / "noaa-etopo2022-60s"

ZENODO_RECORD = "5460860"
PALEO_FILE = "Scotese_Wright_2018_Maps_1-88_6minX6min_PaleoDEMS_nc.zip"
PALEO_URL = f"https://zenodo.org/api/records/{ZENODO_RECORD}/files/{PALEO_FILE}/content"
PALEO_MD5 = "89eb50d8645707ab221b023078535bda"
PALEO_SIZE = 207273848

ETOPO_URL = (
    "https://www.ngdc.noaa.gov/thredds/fileServer/global/ETOPO2022/60s/"
    "60s_surface_elev_netcdf/ETOPO_2022_v1_60s_N90W180_surface.nc"
)
ETOPO_FILE = "ETOPO_2022_v1_60s_N90W180_surface.nc"

# Bedrock companion (same product family, ETOPO 2022 60s). Downloaded so
# render.py can build the (surface - bedrock) ice mask that separates
# Greenland and Antarctica from bare rock.
ETOPO_BED_URL = (
    "https://www.ngdc.noaa.gov/thredds/fileServer/global/ETOPO2022/60s/"
    "60s_bed_elev_netcdf/ETOPO_2022_v1_60s_N90W180_bed.nc"
)
ETOPO_BED_FILE = "ETOPO_2022_v1_60s_N90W180_bed.nc"


def hash_file(path: Path, algo: str = "sha256", chunk: int = 1 << 20) -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for buf in iter(lambda: f.read(chunk), b""):
            h.update(buf)
    return h.hexdigest()


def download(url: str, dst: Path, expected_size: int | None = None, expected_md5: str | None = None) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        actual = dst.stat().st_size
        if expected_size is not None and actual == expected_size:
            print(f"[skip] {dst.name} already {actual} bytes")
            return
        if expected_size is None:
            # Unknown target size: probe once via a HEAD, else re-download from scratch.
            try:
                h = requests.head(url, timeout=60, allow_redirects=True)
                cl = h.headers.get("Content-Length")
                if cl and int(cl) == actual:
                    print(f"[skip] {dst.name} already {actual} bytes (matches HEAD)")
                    return
            except Exception:
                pass
            print(f"[restart] {dst.name} has {actual} bytes but target size unknown; redownloading")
            dst.unlink()
            headers = {}
            mode = "wb"
        else:
            print(f"[resume] {dst.name} {actual}/{expected_size}")
            headers = {"Range": f"bytes={actual}-"}
            mode = "ab"
    else:
        headers = {}
        mode = "wb"

    for attempt in range(1, 5):
        try:
            with requests.get(url, stream=True, headers=headers, timeout=120) as r:
                if r.status_code in (200, 206):
                    with open(dst, mode) as f:
                        got = dst.stat().st_size if mode == "ab" else 0
                        t = time.time()
                        for buf in r.iter_content(chunk_size=1 << 20):
                            if buf:
                                f.write(buf)
                                got += len(buf)
                                if time.time() - t > 5:
                                    print(f"    {dst.name} {got/1e6:.1f} MB")
                                    t = time.time()
                    if expected_md5:
                        got_md5 = hash_file(dst, "md5")
                        if got_md5 != expected_md5:
                            raise RuntimeError(f"md5 mismatch {got_md5} != {expected_md5}")
                    print(f"[ok] {dst.name} {dst.stat().st_size} bytes")
                    return
                else:
                    raise RuntimeError(f"HTTP {r.status_code}")
        except Exception as e:
            print(f"[retry {attempt}] {e}")
            time.sleep(5 * attempt)
    raise RuntimeError(f"Failed to download {url}")


def extract_paleo(zip_path: Path, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    marker = out_dir / ".extracted"
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist()
                 if n.lower().endswith(".nc") and not Path(n).name.startswith("._")]
        need = [n for n in names if not (out_dir / Path(n).name).exists()]
        if need or not marker.exists():
            for n in names:
                target = out_dir / Path(n).name
                if not target.exists() or target.stat().st_size == 0:
                    with zf.open(n) as src, open(target, "wb") as dst:
                        while True:
                            buf = src.read(1 << 20)
                            if not buf:
                                break
                            dst.write(buf)
            marker.write_text("done")
    return sorted(out_dir.glob("*.nc"))


def write_checksums(paleo_zip: Path, etopo_nc: Path, etopo_bed_nc: Path) -> None:
    out = {
        "scotese-paleodem-2018-v2": {
            "file": paleo_zip.name,
            "size_bytes": paleo_zip.stat().st_size,
            "sha256": hash_file(paleo_zip, "sha256"),
            "md5": hash_file(paleo_zip, "md5"),
        },
        "noaa-etopo2022-60s": {
            "files": [
                {
                    "file": etopo_nc.name,
                    "size_bytes": etopo_nc.stat().st_size,
                    "sha256": hash_file(etopo_nc, "sha256"),
                    "md5": hash_file(etopo_nc, "md5"),
                },
                {
                    "file": etopo_bed_nc.name,
                    "size_bytes": etopo_bed_nc.stat().st_size,
                    "sha256": hash_file(etopo_bed_nc, "sha256"),
                    "md5": hash_file(etopo_bed_nc, "md5"),
                },
            ],
            # legacy top-level fields kept for backward compatibility
            "file": etopo_nc.name,
            "size_bytes": etopo_nc.stat().st_size,
            "sha256": hash_file(etopo_nc, "sha256"),
            "md5": hash_file(etopo_nc, "md5"),
        },
    }
    (RAW / "checksums.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


def main() -> int:
    paleo_zip = PALEO_DIR / PALEO_FILE
    etopo_nc = ETOPO_DIR / ETOPO_FILE
    etopo_bed_nc = ETOPO_DIR / ETOPO_BED_FILE

    download(PALEO_URL, paleo_zip, PALEO_SIZE, PALEO_MD5)
    download(ETOPO_URL, etopo_nc)
    download(ETOPO_BED_URL, etopo_bed_nc)

    nc_files = extract_paleo(paleo_zip, PALEO_DIR / "nc")
    print(f"paleo netcdfs: {len(nc_files)}")

    write_checksums(paleo_zip, etopo_nc, etopo_bed_nc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
