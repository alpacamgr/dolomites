"""Download Seguinot et al. (2018) Alpine ice-sheet 1 km continuous-variables file.

Target: alpcyc.1km.epic.pp.ex.1ka.nc from Zenodo record 1423176.
The 1 km run with EPICA-Dome-C temperature forcing and palaeo-precipitation
reduction (`pp`) is the recommended reference run; 1 kyr snapshots 120..0 ka.
Idempotent: resumes if a partial file exists, verifies MD5 on completion.
"""
from __future__ import annotations

import hashlib
import os
import sys
import time
from pathlib import Path

import requests

URL = "https://zenodo.org/api/records/1423176/files/alpcyc.1km.epic.pp.ex.1ka.nc/content"
DEST = Path("E:/Projects/Dolomites/data/raw/seguinot2018-alps-1km/alpcyc.1km.epic.pp.ex.1ka.nc")
EXPECTED_MD5 = "2280c6c6f01a972a8cfa3ac75e080bf5"
EXPECTED_SIZE = 410955896


def md5sum(p: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.md5()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def main() -> int:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists() and DEST.stat().st_size == EXPECTED_SIZE:
        print(f"already have full file at {DEST}")
        got = md5sum(DEST)
        if got == EXPECTED_MD5:
            print("md5 ok:", got)
            return 0
        print("md5 mismatch, redownloading. got=", got)
        DEST.unlink()

    have = DEST.stat().st_size if DEST.exists() else 0
    headers = {"Range": f"bytes={have}-"} if have else {}
    mode = "ab" if have else "wb"
    print(f"downloading {URL}  resume-from={have}", flush=True)
    with requests.get(URL, stream=True, timeout=60, headers=headers) as r:
        if r.status_code == 416:
            # already complete
            print("server says done (416)")
        else:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length", "0")) + have
            with DEST.open(mode) as f:
                start = time.time()
                last = start
                dl = have
                for chunk in r.iter_content(1024 * 1024):
                    if not chunk:
                        continue
                    f.write(chunk)
                    dl += len(chunk)
                    now = time.time()
                    if now - last > 5:
                        pct = 100.0 * dl / max(total, 1)
                        mbs = (dl - have) / (now - start) / (1024 * 1024)
                        print(f"  {dl/1e6:9.1f}/{total/1e6:9.1f} MB  {pct:5.1f}%  {mbs:5.2f} MB/s", flush=True)
                        last = now
    size = DEST.stat().st_size
    if size != EXPECTED_SIZE:
        print(f"size mismatch {size} != {EXPECTED_SIZE}", file=sys.stderr)
        return 1
    got = md5sum(DEST)
    if got != EXPECTED_MD5:
        print(f"md5 mismatch got={got} expected={EXPECTED_MD5}", file=sys.stderr)
        return 1
    print("OK   size", size, "md5", got)
    return 0


if __name__ == "__main__":
    sys.exit(main())
