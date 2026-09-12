"""Generate a contact sheet of all texture slices and full-size previews for
a few notable ages. Also compute total disk usage.

Reads from app/public/data/globe/textures/{2k,4k}/{age}.webp. Writes into
data/processed/textures/preview/.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = ROOT / "app" / "public" / "data" / "globe" / "textures"
PROC_DIR = ROOT / "data" / "processed" / "textures"
PREVIEW = PROC_DIR / "preview"
FULL_AGES = [0, 5, 240]
THUMB_W, THUMB_H = 320, 160  # 2:1 aspect
COLS = 8


def dir_size(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def build_contact_sheet(ages: list[int]) -> None:
    n = len(ages)
    cols = COLS
    rows = (n + cols - 1) // cols
    label_h = 22
    pad = 8
    cell_w = THUMB_W + pad
    cell_h = THUMB_H + label_h + pad
    W = cols * cell_w + pad
    H = rows * cell_h + pad
    sheet = Image.new("RGB", (W, H), (30, 30, 34))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font = ImageFont.load_default()

    for k, age in enumerate(ages):
        r, c = divmod(k, cols)
        x = pad + c * cell_w
        y = pad + r * cell_h
        src = OUT_DIR / "2k" / f"{age}.webp"
        if src.exists():
            im = Image.open(src)
            im.thumbnail((THUMB_W, THUMB_H))
            sheet.paste(im, (x, y))
            label = f"{age} Ma" + (" (obs)" if age == 0 else "")
        else:
            draw.rectangle([x, y, x + THUMB_W, y + THUMB_H], outline=(90, 90, 100), fill=(45, 45, 50))
            label = f"{age} Ma (missing)"
        draw.text((x + 4, y + THUMB_H + 4), label, fill=(220, 220, 220), font=font)
    out = PREVIEW / "contact_sheet.png"
    PREVIEW.mkdir(parents=True, exist_ok=True)
    sheet.save(out, optimize=True)
    print(f"[contact sheet] {out} {out.stat().st_size/1e6:.2f} MB")


def dump_full_previews(ages: list[int]) -> None:
    for age in ages:
        src = OUT_DIR / "4k" / f"{age}.webp"
        if not src.exists():
            print(f"[warn] missing {src}")
            continue
        im = Image.open(src)
        out = PREVIEW / f"full_{age}Ma.png"
        im.save(out, optimize=True)
        print(f"[full] {out} {out.stat().st_size/1e6:.2f} MB")


def report_sizes() -> dict:
    sizes = {
        "4k_bytes": dir_size(OUT_DIR / "4k"),
        "2k_bytes": dir_size(OUT_DIR / "2k"),
        "textures_total_bytes": dir_size(OUT_DIR),
    }
    n4 = len(list((OUT_DIR / "4k").glob("*.webp"))) if (OUT_DIR / "4k").exists() else 0
    n2 = len(list((OUT_DIR / "2k").glob("*.webp"))) if (OUT_DIR / "2k").exists() else 0
    sizes["files_4k"] = n4
    sizes["files_2k"] = n2
    return sizes


def main() -> int:
    if not OUT_DIR.exists():
        print(f"missing {OUT_DIR}")
        return 1
    idx_path = OUT_DIR / "index.json"
    if idx_path.exists():
        idx = json.loads(idx_path.read_text())
        ages = idx["ages_ma"]
    else:
        ages = [int(p.stem) for p in sorted((OUT_DIR / "2k").glob("*.webp"), key=lambda x: int(x.stem))]
    build_contact_sheet(ages)
    dump_full_previews(FULL_AGES)
    sizes = report_sizes()
    (PREVIEW / "sizes.json").write_text(json.dumps(sizes, indent=2))
    print(json.dumps(sizes, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
