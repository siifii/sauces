#!/usr/bin/env python3
"""Extract a color palette from design images (Sauces).

Runs k-means on pixels (Pillow + numpy), outputs hex colors with coverage %,
and merges near-duplicates whose CIE ΔE is below a threshold.

Pools all opaque pixels (alpha >= 128) of all images, clusters them in Lab with
k-means++ (seed 0), merges clusters closer than --merge-delta-e (CIE76), drops
clusters under 0.5% coverage and renormalizes. Output JSON:
{"version": 1, "colors": [{"hex": "#RRGGBB", "coverage": 0.0-1.0}, ...]}.
Exit codes: 0 ok, 2 unreadable image, 3 missing dependency.
"""
import argparse
import json
import sys

MAX_PIXELS = 200_000
MIN_COVERAGE = 0.005


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
        prog="extract_palette.py",
        description="Extract a palette (hex + coverage %) from one or more images.",
    )
    p.add_argument("images", nargs="+", help="PNG/JPG files to analyse")
    p.add_argument("-k", "--clusters", type=int, default=12, help="k-means cluster count (default: 12)")
    p.add_argument("--merge-delta-e", type=float, default=3.0,
                   help="merge colors closer than this ΔE (default: 3.0)")
    p.add_argument("-o", "--output", help="write JSON here instead of stdout")
    return p.parse_args(argv)


def load_pixels(paths, max_pixels=MAX_PIXELS, seed=0):
    """Return (N, 3) uint8 array of opaque pixels pooled over all images.

    Each image is converted to RGBA, transparent pixels (alpha < 128) are
    dropped, then it is downsampled independently to at most max_pixels
    using a seeded RNG. Raises ValueError(path) for unreadable files.
    """
    import numpy as np
    from PIL import Image

    rng = np.random.default_rng(seed)
    chunks = []
    for path in paths:
        try:
            with Image.open(path) as img:
                rgba = np.asarray(img.convert("RGBA"))
        except Exception as exc:
            raise ValueError(path) from exc
        flat = rgba.reshape(-1, 4)
        px = flat[flat[:, 3] >= 128][:, :3]
        if len(px) > max_pixels:
            px = px[np.sort(rng.choice(len(px), max_pixels, replace=False))]
        if len(px):
            chunks.append(px)
    if not chunks:
        return np.empty((0, 3), dtype=np.uint8)
    return np.concatenate(chunks).astype(np.uint8)


_M = [[0.4124564, 0.3575761, 0.1804375],
      [0.2126729, 0.7151522, 0.0721750],
      [0.0193339, 0.1191920, 0.9503041]]
_WHITE = [0.95047, 1.0, 1.08883]  # D65


def srgb_to_lab(rgb):
    """sRGB (0-255, shape (...,3)) -> CIE Lab (D65), float64."""
    import numpy as np

    c = np.asarray(rgb, dtype=np.float64) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    xyz = lin @ np.array(_M).T / np.array(_WHITE)
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16,
                     500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])], axis=-1)


def lab_to_srgb(lab):
    """CIE Lab (D65) -> sRGB uint8, clamped to gamut."""
    import numpy as np

    lab = np.asarray(lab, dtype=np.float64)
    fy = (lab[..., 0] + 16) / 116
    f = np.stack([fy + lab[..., 1] / 500, fy, fy - lab[..., 2] / 200], axis=-1)
    xyz = np.where(f ** 3 > 216 / 24389, f ** 3, (116 * f - 16) / (24389 / 27))
    lin = (xyz * np.array(_WHITE)) @ np.linalg.inv(np.array(_M)).T
    lin = np.clip(lin, 0.0, 1.0)
    c = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)
    return np.clip(np.rint(c * 255), 0, 255).astype(np.uint8)


def _sq_dist(points, centers):
    import numpy as np

    return ((points[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)


def kmeans(pixels, k, seed=0, iters=20):
    """k-means with k-means++ init. Returns (centers (k,3) float, counts (k,) int).

    pixels is any (N,3) numeric array (the CLI passes Lab values). k is capped
    at the number of distinct points. Empty clusters are re-seeded from the
    point farthest from its center, so results are deterministic.
    """
    import numpy as np

    pts = np.asarray(pixels, dtype=np.float64)
    k = max(1, min(k, len(np.unique(pts, axis=0))))
    rng = np.random.default_rng(seed)
    centers = [pts[rng.integers(len(pts))]]
    d2 = _sq_dist(pts, np.array(centers))[:, 0]
    while len(centers) < k:
        total = d2.sum()
        idx = int(rng.choice(len(pts), p=d2 / total)) if total > 0 else int(np.argmax(d2))
        centers.append(pts[idx])
        d2 = np.minimum(d2, ((pts - pts[idx]) ** 2).sum(axis=1))
    centers = np.array(centers)

    for _ in range(iters):
        dist = _sq_dist(pts, centers)
        labels = dist.argmin(axis=1)
        new = centers.copy()
        for j in range(k):
            members = pts[labels == j]
            if len(members):
                new[j] = members.mean(axis=0)
            else:
                far = int(dist[np.arange(len(pts)), labels].argmax())
                new[j] = pts[far]
                labels[far] = j
        if np.allclose(new, centers):
            centers = new
            break
        centers = new
    labels = _sq_dist(pts, centers).argmin(axis=1)
    return centers, np.bincount(labels, minlength=k)


def merge_close(colors, threshold):
    """Merge (lab, weight) entries whose CIE76 distance is below threshold.

    Repeatedly merges the closest pair using a weight-averaged Lab mean until
    no pair is below the threshold. Returns a list of (lab ndarray, weight).
    """
    import numpy as np

    items = [(np.asarray(lab, dtype=np.float64), float(w)) for lab, w in colors]
    while len(items) > 1:
        best, pair = threshold, None
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                d = float(np.linalg.norm(items[i][0] - items[j][0]))
                if d < best:
                    best, pair = d, (i, j)
        if pair is None:
            break
        i, j = pair
        (la, wa), (lb, wb) = items[i], items[j]
        w = wa + wb
        merged = ((la * wa + lb * wb) / w if w > 0 else la, w)
        items = [it for n, it in enumerate(items) if n not in (i, j)] + [merged]
    return items


def build_palette(pixels, k, merge_delta_e):
    """Pixels (N,3 uint8) -> list of {"hex", "coverage"} sorted by coverage desc."""
    if len(pixels) == 0:
        return []
    centers, counts = kmeans(srgb_to_lab(pixels), k)
    keep = counts > 0
    total = float(counts.sum())
    merged = merge_close(zip(centers[keep], counts[keep] / total), merge_delta_e)
    merged = [(lab, w) for lab, w in merged if w >= MIN_COVERAGE]
    norm = sum(w for _, w in merged)
    out = []
    for lab, w in merged:
        r, g, b = (int(v) for v in lab_to_srgb(lab))
        out.append({"hex": f"#{r:02X}{g:02X}{b:02X}", "coverage": round(w / norm, 4)})
    out.sort(key=lambda c: (-c["coverage"], c["hex"]))
    return out


def main(argv=None):
    args = parse_args(argv)
    if args.clusters < 1:
        print("--clusters must be >= 1", file=sys.stderr)
        return 2
    require_deps()
    try:
        pixels = load_pixels(args.images)
    except ValueError as exc:
        print(f"cannot read image: {exc.args[0]}", file=sys.stderr)
        return 2
    result = {"version": 1, "colors": build_palette(pixels, args.clusters, args.merge_delta_e)}
    text = json.dumps(result, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
