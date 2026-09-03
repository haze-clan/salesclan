#!/usr/bin/env python3
"""
Generate the Chrome Ledger home-screen icon (Apple touch icon).

Draws at 4x and downsamples for clean edges. Output is embedded into the
dashboard as a base64 data URI (see render_dashboard.py) since Artifact
pages can't reference relative image files.
"""
from __future__ import annotations

import base64
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "icons"
SCALE = 4
SIZE = 180 * SCALE

VOID = (13, 13, 16)
SIGNAL = (252, 238, 10)
SIGNAL_DIM = (122, 115, 10)
ICE = (0, 229, 255)

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def build_icon() -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE), VOID)
    draw = ImageDraw.Draw(img)

    # corner-cut accent triangles, echoing the dashboard's panel motif
    cut = int(SIZE * 0.22)
    draw.polygon(
        [(SIZE - cut, 0), (SIZE, 0), (SIZE, cut)],
        fill=SIGNAL_DIM,
    )
    draw.polygon(
        [(0, SIZE - cut), (0, SIZE), (cut, SIZE)],
        fill=SIGNAL_DIM,
    )

    # thin ice baseline rule
    rule_y = int(SIZE * 0.74)
    rule_margin = int(SIZE * 0.24)
    draw.rectangle(
        [rule_margin, rule_y, SIZE - rule_margin, rule_y + int(SIZE * 0.012)],
        fill=ICE,
    )

    # "CL" monogram
    font = ImageFont.truetype(FONT_PATH, int(SIZE * 0.46))
    text = "CL"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (SIZE - tw) / 2 - bbox[0]
    ty = (SIZE - th) / 2 - bbox[1] - int(SIZE * 0.05)
    draw.text((tx, ty), text, font=font, fill=SIGNAL)

    return img.resize((180, 180), Image.LANCZOS)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    icon = build_icon()
    png_path = OUT_DIR / "apple-touch-icon-180.png"
    icon.save(png_path)

    b64 = base64.b64encode(png_path.read_bytes()).decode("ascii")
    data_uri_path = OUT_DIR / "apple-touch-icon-180.b64.txt"
    data_uri_path.write_text(b64)
    print(f"Wrote {png_path} ({png_path.stat().st_size} bytes)")
    print(f"Wrote {data_uri_path} ({len(b64)} b64 chars)")


if __name__ == "__main__":
    main()
