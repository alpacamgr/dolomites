"""Download GLACIMONTIS SHP archive from Zenodo record 15600659."""
import hashlib, sys, time
from pathlib import Path
import requests

URL = 'https://zenodo.org/api/records/15600659/files/GLACIMONTIS_SHP.zip/content'
DEST = Path('E:/Projects/Dolomites/data/raw/glacimontis-2026/GLACIMONTIS_SHP.zip')
EXPECTED_SIZE = 130153904


def main():
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists() and DEST.stat().st_size == EXPECTED_SIZE:
        print('already have file')
        return 0
    have = DEST.stat().st_size if DEST.exists() else 0
    headers = {'Range': f'bytes={have}-'} if have else {}
    mode = 'ab' if have else 'wb'
    with requests.get(URL, stream=True, timeout=120, headers=headers) as r:
        r.raise_for_status()
        with DEST.open(mode) as f:
            dl = have
            start = time.time()
            last = start
            for c in r.iter_content(1024*1024):
                if not c: continue
                f.write(c); dl += len(c)
                now = time.time()
                if now - last > 5:
                    print(f'{dl/1e6:.1f}/{EXPECTED_SIZE/1e6:.1f} MB', flush=True); last = now
    h = hashlib.sha256(DEST.read_bytes()).hexdigest()
    print('OK', DEST.stat().st_size, h)


if __name__ == '__main__':
    sys.exit(main() or 0)
