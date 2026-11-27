#!/usr/bin/env python3
"""Dev-only: build the README demo GIF from a real Sauces run.

Reads a target project's .sauces/ folder (manifest references, verify renders, diffs, RTL
captures and summary scores) and writes an animated GIF: design -> built -> difference ->
phone + RTL -> report. Pillow only.

Usage:
  make_demo_gif.py --sauces-dir <project>/.sauces [--report-png report.png] [--out assets/demo.gif]
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
FONTS = REPO / "examples" / "designs" / "login" / "src" / "fonts"
W, H = 960, 600
BAR = 64
BRAND = (61, 90, 254)
INK = (27, 27, 31)
PAPER = (246, 246, 250)


def font(size, weight="SemiBold"):
    try:
        return ImageFont.truetype(str(FONTS / f"Inter-{weight}.ttf"), size)
    except OSError:
        return ImageFont.load_default()


def fit(img, box_w, box_h):
    img = img.convert("RGB")
    scale = min(box_w / img.width, box_h / img.height)
    return img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)


def frame(title, subtitle, panels):
    """panels: [(image, label)] laid out side by side under a caption bar."""
    canvas = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, W, BAR), fill=BRAND)
    draw.text((24, 12), title, font=font(24), fill="white")
    draw.text((24, 40), subtitle, font=font(14, "Regular"), fill=(225, 230, 255))
    gap, pad = 16, 24
    n = len(panels)
    box_w = (W - 2 * pad - gap * (n - 1)) // n
    box_h = H - BAR - 2 * pad - 24
    x = pad
    for img, label in panels:
        shot = fit(img, box_w, box_h)
        ox = x + (box_w - shot.width) // 2
        oy = BAR + pad + (box_h - shot.height) // 2
        draw.rectangle((ox - 1, oy - 1, ox + shot.width, oy + shot.height), outline=(210, 210, 220))
        canvas.paste(shot, (ox, oy))
        tw = draw.textlength(label, font=font(14))
        draw.text((x + (box_w - tw) / 2, H - pad - 18), label, font=font(14), fill=INK)
        x += box_w + gap
    return canvas


def main(argv=None):
    p = argparse.ArgumentParser(description="Build the README demo GIF from a Sauces run's .sauces folder.")
    p.add_argument("--sauces-dir", required=True, type=Path)
    p.add_argument("--report-png", type=Path, help="screenshot of the run's report.html (optional)")
    p.add_argument("--out", type=Path, default=REPO / "assets" / "demo.gif")
    args = p.parse_args(argv)

    sauces = args.sauces_dir
    summary = json.loads((sauces / "verify" / "summary.json").read_text())
    results = {r["id"]: r for r in summary["results"]}
    root = sauces.parent

    def state(rid):
        r = results[rid]
        it = sauces / "verify" / rid / f"iter-{r.get('iterations') or 1}"
        return (Image.open(root / r["reference"]), Image.open(it / "rendered.png"),
                Image.open(it / "diff.png"), r["score"])

    wide = sorted((rid for rid in results if rid.endswith("--default")),
                  key=lambda rid: -int(rid.split("@")[1].split("--")[0]) if "@" in rid else 0)
    if not wide:
        print("no default states in summary.json", file=sys.stderr)
        return 1
    big, small = wide[0], wide[-1]
    ref, built, diff, score = state(big)
    frames = [
        frame("1. Your design", "A PNG, PDF, SVG or Figma frame", [(ref, big)]),
        frame("2. Built in your project", f"{summary['platform']}: your components, tokens and i18n",
              [(built, "built")]),
        frame("3. Rendered and scored", f"Pixel + SSIM comparison: {score:.1f} / 100",
              [(built, "built"), (diff, "difference from the design")]),
    ]
    if small != big:
        sref, sbuilt, _, sscore = state(small)
        panels = [(sref, "phone design"), (sbuilt, f"built · {sscore:.1f}")]
        rtl = sauces / "verify" / small / "rtl.png"
        if rtl.is_file():
            panels.append((Image.open(rtl), "right-to-left"))
        frames.append(frame("4. Every width, and right-to-left", "Each designed breakpoint is verified",
                            panels))
    if args.report_png:
        frames.append(frame("5. A report you can share", "Fidelity, reuse, translations, design audit",
                            [(Image.open(args.report_png), "report.html")]))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    pal = [f.convert("P", palette=Image.ADAPTIVE, colors=128) for f in frames]
    pal[0].save(args.out, save_all=True, append_images=pal[1:], duration=2200, loop=0, optimize=True)
    print(f"wrote {args.out} ({len(frames)} frames, {args.out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
