#!/usr/bin/env python3
"""Extract a color palette from design images (Sauces).

Runs k-means on pixels (Pillow + numpy), outputs hex colors with coverage %,
and merges near-duplicates whose CIE ΔE is below a threshold.

Stub: implemented in Phase 3.
"""
import argparse
import sys


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


def main(argv=None):
    parse_args(argv)
    print("extract_palette.py: not implemented yet (Phase 3)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
