#!/usr/bin/env python3
"""Rasterize PDF pages to PNG for design ingestion (Sauces).

Uses pdftoppm when it is on PATH; otherwise exits with a clear error.

Stub: implemented in Phase 3.
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
        prog="rasterize_pdf.py",
        description="Rasterize each page of a PDF to PNG (requires pdftoppm).",
    )
    p.add_argument("pdf", help="input PDF file")
    p.add_argument("--out-dir", required=True, help="directory for page PNGs")
    p.add_argument("--dpi", type=int, default=144, help="render resolution (default: 144)")
    return p.parse_args(argv)


def main(argv=None):
    parse_args(argv)
    require_deps()
    print("rasterize_pdf.py: not implemented yet (Phase 3)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
