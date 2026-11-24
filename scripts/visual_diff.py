#!/usr/bin/env python3
"""Score a rendered UI image against its design reference (Sauces).

Resizes to match, computes pixel diff % and SSIM (numpy implementation),
writes a heatmap diff.png and score.json, and prints a combined 0-100 score.

score = round(100 * (0.4 * pixel_similarity + 0.6 * ssim), 1). Exit 0 if the score
reaches --threshold, 1 if not, 2 on usage error, 3 on missing dependency.
"""
import argparse
import json
import sys
from pathlib import Path

TOLERANCE = 16
WIN = 7
K1, K2, L = 0.01, 0.03, 255.0


def require_deps() -> None:
    """Exit 3 with an install hint if Pillow or numpy is missing."""
    for module, name in (("PIL", "PIL"), ("numpy", "numpy")):
        try:
            __import__(module)
        except ImportError:
            print(f"Missing dependency: {name}. Install with: python3 -m pip install pillow numpy",
                  file=sys.stderr)
            raise SystemExit(3)


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="visual_diff.py",
        description="Compare a rendered PNG with a reference PNG and output a 0-100 fidelity score.",
    )
    p.add_argument("rendered", help="rendered screenshot (PNG)")
    p.add_argument("reference", help="design reference (PNG)")
    p.add_argument("--out-dir", default=".", help="where to write diff.png and score.json (default: .)")
    p.add_argument("--threshold", type=float, default=90.0, help="pass threshold (default: 90)")
    return p.parse_args(argv)


def load_rgb(path):
    """Load an image as an (H, W, 3) uint8 array; RGBA is composited on white."""
    import numpy as np
    from PIL import Image

    img = Image.open(path)
    img.load()
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, rgba)
    return np.asarray(img.convert("RGB"), dtype=np.uint8)


def pixel_similarity(a, b, tolerance=TOLERANCE):
    """Fraction of pixels whose max per-channel absolute difference is <= tolerance."""
    import numpy as np

    diff = np.abs(a.astype(np.int16) - b.astype(np.int16)).max(axis=2)
    return float((diff <= tolerance).mean())


def _luma(a):
    import numpy as np

    f = a.astype(np.float64)
    return 0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]


def _box_mean(x, win=WIN):
    """Mean over every valid win x win window, via a summed-area table."""
    import numpy as np

    sat = np.zeros((x.shape[0] + 1, x.shape[1] + 1), dtype=np.float64)
    sat[1:, 1:] = x.cumsum(axis=0).cumsum(axis=1)
    total = sat[win:, win:] - sat[:-win, win:] - sat[win:, :-win] + sat[:-win, :-win]
    return total / (win * win)


def ssim(a, b):
    """Mean SSIM on BT.601 luminance, 7x7 uniform window, valid windows only, clipped to [0, 1].

    If either dimension is under 7 px no window fits, so this returns pixel_similarity(a, b).
    """
    import numpy as np

    h, w = a.shape[:2]
    if h < WIN or w < WIN:
        return pixel_similarity(a, b)
    x, y = _luma(a), _luma(b)
    mx, my = _box_mean(x), _box_mean(y)
    vx = _box_mean(x * x) - mx * mx
    vy = _box_mean(y * y) - my * my
    cxy = _box_mean(x * y) - mx * my
    c1, c2 = (K1 * L) ** 2, (K2 * L) ** 2
    m = ((2 * mx * my + c1) * (2 * cxy + c2)) / ((mx * mx + my * my + c1) * (vx + vy + c2))
    return float(np.clip(m.mean(), 0.0, 1.0))


def score(pixel_sim, ssim_value):
    return round(100 * (0.4 * pixel_sim + 0.6 * ssim_value), 1)


def heatmap(ref, rend):
    """Reference as 40% grayscale, with differing pixels painted red by intensity."""
    import numpy as np

    gray = (_luma(ref) * 0.4)[..., None]
    out = np.repeat(gray, 3, axis=2)
    diff = np.abs(ref.astype(np.int16) - rend.astype(np.int16)).max(axis=2)
    mask = diff > TOLERANCE
    alpha = np.clip(diff / 255.0, 0.35, 1.0)[..., None]
    red = np.array([255.0, 0.0, 0.0])
    out = np.where(mask[..., None], out * (1 - alpha) + red * alpha, out)
    return np.clip(out, 0, 255).astype(np.uint8)


def _read(path):
    try:
        return load_rgb(path)
    except Exception:
        print(f"cannot read image: {path}", file=sys.stderr)
        raise SystemExit(2)


def main(argv=None):
    args = parse_args(argv)
    if not 0 <= args.threshold <= 100:
        print("--threshold must be between 0 and 100", file=sys.stderr)
        return 2
    require_deps()
    from PIL import Image
    import numpy as np

    rend = _read(args.rendered)
    ref = _read(args.reference)
    if rend.shape != ref.shape:
        h, w = ref.shape[:2]
        rend = np.asarray(Image.fromarray(rend).resize((w, h), Image.LANCZOS), dtype=np.uint8)

    ps = pixel_similarity(rend, ref)
    sv = ssim(rend, ref)
    sc = score(ps, sv)
    passed = bool(sc >= args.threshold)
    h, w = ref.shape[:2]

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    Image.fromarray(heatmap(ref, rend)).save(out / "diff.png")
    (out / "score.json").write_text(json.dumps({
        "version": 1, "score": sc, "pixel_similarity": round(ps, 4), "ssim": round(sv, 4),
        "threshold": args.threshold, "passed": passed, "size": [w, h],
    }, indent=2) + "\n")
    print(sc)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
