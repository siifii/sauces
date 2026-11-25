#!/usr/bin/env python3
"""Rasterize PDF pages to PNG for design ingestion (Sauces).

Shells out to pdftoppm (poppler). Needs no Pillow or numpy.
Prints {"version":1,"pages":["<out-dir>/page-001.png", ...]} on success.
Exit codes: 0 ok, 1 render failed, 2 PDF not found, 4 pdftoppm missing.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

PAGE_RE = re.compile(r"^page-\d+\.png$")
TMP_RE = re.compile(r"^.+-(\d+)\.png$")


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
    args = parse_args(argv)
    if not os.path.isfile(args.pdf):
        print(f"PDF not found: {args.pdf}", file=sys.stderr)
        return 2
    exe = shutil.which("pdftoppm")
    if not exe:
        print("pdftoppm not found. Install poppler (macOS: brew install poppler; "
              "Debian/Ubuntu: apt install poppler-utils).", file=sys.stderr)
        return 4

    os.makedirs(args.out_dir, exist_ok=True)
    # Remove stale page-NNN.png files from a previous run; touch nothing else.
    for name in os.listdir(args.out_dir):
        if PAGE_RE.match(name):
            os.remove(os.path.join(args.out_dir, name))

    with tempfile.TemporaryDirectory(prefix=".rasterize-", dir=args.out_dir) as tmp:
        try:
            r = subprocess.run([exe, "-png", "-r", str(args.dpi), args.pdf, os.path.join(tmp, "p")],
                               capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            print("pdftoppm timed out", file=sys.stderr)
            return 1
        if r.returncode != 0:
            print(f"pdftoppm failed: {r.stderr.strip()}", file=sys.stderr)
            return 1
        found = []
        for name in os.listdir(tmp):
            m = TMP_RE.match(name)
            if m:
                found.append((int(m.group(1)), name))
        found.sort()
        if not found:
            print("pdftoppm failed: no pages produced", file=sys.stderr)
            return 1
        pages = []
        for num, name in found:
            final = f"page-{num:03d}.png"
            os.replace(os.path.join(tmp, name), os.path.join(args.out_dir, final))
            pages.append(f"{args.out_dir.rstrip('/') or '/'}/{final}")
    print(json.dumps({"version": 1, "pages": pages}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
