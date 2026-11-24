#!/usr/bin/env python3
"""Score a rendered UI image against its design reference (Sauces).

Resizes to match, computes pixel diff % and SSIM (numpy implementation),
writes a heatmap diff.png and score.json, and prints a combined 0-100 score.

Stub: implemented in Phase 6.
"""
import argparse
import sys


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


def main(argv=None):
    parse_args(argv)
    require_deps()
    print("visual_diff.py: not implemented yet (Phase 6)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
