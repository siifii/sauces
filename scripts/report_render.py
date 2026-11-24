#!/usr/bin/env python3
"""Render the Sauces report.html from pipeline JSON outputs.

Fills skills/report/assets/report-template.html from manifest, project
profile, plan and verify results into one self-contained HTML file.

Stub: implemented in Phase 7.
"""
import argparse
import sys


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="report_render.py",
        description="Build .sauces/report.html from the .sauces/ working state.",
    )
    p.add_argument("--sauces-dir", default=".sauces", help="path to the .sauces/ folder (default: .sauces)")
    p.add_argument("--template", help="HTML template (default: the plugin's report-template.html)")
    p.add_argument("-o", "--output", help="output file (default: <sauces-dir>/report.html)")
    return p.parse_args(argv)


def main(argv=None):
    parse_args(argv)
    print("report_render.py: not implemented yet (Phase 7)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
