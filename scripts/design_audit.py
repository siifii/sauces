#!/usr/bin/env python3
"""Measure design facts in .sauces/manifest.json and write .sauces/design-audit.json (Sauces).

Stdlib only. Reads the manifest's tokens and every state's `layout` tree (logical
px) and measures, without judging taste:

  accessibility  text contrast (WCAG 2.2 SC 1.4.3), UI-component border contrast
                 (SC 1.4.11), touch targets of interactive components (Material
                 48 x 48 dp, HIG 44 x 44 pt, WCAG SC 2.5.8 24 x 24), text under 12 px
  consistency    near-duplicate colors (CIE76 delta E < 3), spacing and radius
                 values off the 4-pt grid
  states         missing loading / empty / error states (screens with inputs
                 expect loading + error, screens with lists expect empty + loading)

Each finding: {id: audit-<category>-<n>, category, severity: high|medium|low,
screen, state?, also_in?, region?, detail, measured: {...numbers...}, guideline}.
Findings are facts for the plan skill to turn into design suggestions; they are
not failures.

Text contrast pairs a text's `style.color` with the background of the nearest
node (itself, then ancestors) that has `style.background`; with none, the color
token named surface/background, else #FFFFFF. `measured.background_source` says
which.

Exit codes: 0 audit written (findings or not), 2 usage error or an unreadable /
invalid manifest.
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

CATEGORIES = ["accessibility", "consistency", "states", "platform", "localization", "ux"]
SEVERITIES = ["high", "medium", "low"]

INTERACTIVE_KINDS = {"button", "icon-button", "link", "text-field", "checkbox", "radio",
                     "switch", "chip", "list-item"}
INPUT_KINDS = {"text-field", "checkbox", "radio", "switch"}
BORDERED_KINDS = {"text-field", "checkbox", "radio", "switch", "chip", "button"}

G_CONTRAST = ("WCAG 2.2 SC 1.4.3 Contrast (Minimum), level AA: 4.5:1 for normal text, "
              "3:1 for large text (>= 24 px, or >= 18.66 px bold)")
G_NONTEXT = ("WCAG 2.2 SC 1.4.11 Non-text Contrast, level AA: 3:1 for the visual boundary "
             "that identifies a UI component against adjacent colors")
G_TARGET = ("Material 3 accessibility: touch targets at least 48 x 48 dp; Apple HIG: at least "
            "44 x 44 pt; WCAG 2.2 SC 2.5.8 Target Size (Minimum), level AA: 24 x 24 CSS px "
            "(inline links in a sentence are exempt)")
G_SMALL_TEXT = ("Legibility recommendation, not a WCAG requirement: Material 3's smallest type "
                "role (label small) is 11 sp and body text starts at 12 sp; Apple HIG's "
                "smallest default text style (caption 2) is 11 pt. Text under 12 px is hard to "
                "read for many users; whatever the size, it must scale with the system text "
                "size (WCAG 2.2 SC 1.4.4 Resize Text)")
G_DUP_COLOR = ("Design-token consistency: colors within CIE76 delta E 3 are hard to tell apart "
               "and usually mean one intended color; Material 3 color roles map each purpose "
               "to one token")
G_GRID = ("Material 3 layout and Apple HIG layout use spacing on a 4-pt grid (Material: 4 dp "
          "increments, 8 dp baseline); off-grid values usually mean a measurement or intent gap")
G_STATES = ("Material 3 communication patterns and Apple HIG feedback: show progress while "
            "waiting (loading), explain what failed and how to recover (error), and say why a "
            "list is empty and what to do (empty)")


class ManifestError(Exception):
    pass


# ---------------------------------------------------------------- colors

def parse_hex(value):
    """'#RRGGBB', '#RRGGBBAA' or '#RGB' -> (r, g, b) ints, else None."""
    if not isinstance(value, str):
        return None
    m = re.fullmatch(r"#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", value.strip())
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def norm_hex(value):
    rgb = parse_hex(value)
    return "#%02X%02X%02X" % rgb if rgb else None


def _to_rgb(value):
    rgb = parse_hex(value)
    if rgb is None:
        raise ValueError(f"not a hex color: {value!r}")
    return rgb


def _linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color):
    r, g, b = (_linear(c) for c in _to_rgb(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg, bg):
    """WCAG 2.x contrast ratio between two hex colors (1.0 .. 21.0)."""
    a, b = relative_luminance(fg), relative_luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def _lab(hex_color):
    r, g, b = (_linear(c) for c in _to_rgb(hex_color))
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = (0.2126729 * r + 0.7151522 * g + 0.0721750 * b) / 1.0
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > (6 / 29) ** 3 else t / (3 * (6 / 29) ** 2) + 4 / 29

    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e76(hex_a, hex_b):
    """CIE76 delta E between two sRGB hex colors (D65)."""
    return math.dist(_lab(hex_a), _lab(hex_b))


def near_duplicate_colors(hexes, threshold=3.0):
    """Pairs (a, b, delta_e) of distinct colors closer than threshold, closest first."""
    uniq = sorted({h for h in (norm_hex(x) for x in hexes) if h})
    pairs = []
    for i, a in enumerate(uniq):
        for b in uniq[i + 1:]:
            d = delta_e76(a, b)
            if d < threshold:
                pairs.append((a, b, round(d, 2)))
    return sorted(pairs, key=lambda p: (p[2], p[0], p[1]))


# ---------------------------------------------------------------- spacing

def _off_grid(value, grid, tolerance=0.5):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 3:
        return False  # 0 and hairline values (< 3, snapped to 2 by ingest) are allowed
    return abs(value - round(value / grid) * grid) > tolerance


def spacing_outliers(values, grid=4):
    """Distinct values off the grid by more than 0.5 px (values under 3 count as hairlines)."""
    return sorted({v for v in values if _off_grid(v, grid)})


# ---------------------------------------------------------------- layout walking

def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _label(node):
    comp = node.get("component") if isinstance(node.get("component"), dict) else None
    name = comp.get("kind", "component") if comp else node.get("type", "node")
    text = node.get("text")
    if isinstance(text, str) and text:
        short = text if len(text) <= 32 else text[:29] + "..."
        return f'{name} "{short}"'
    return str(name)


def iter_nodes(manifest):
    """Yield (screen_id, state_name, node, ancestors) for every layout node."""
    for screen in manifest.get("screens") or []:
        if not isinstance(screen, dict):
            continue
        for state in screen.get("states") or []:
            if not isinstance(state, dict) or not isinstance(state.get("layout"), dict):
                continue
            stack = [(state["layout"], ())]
            while stack:
                node, anc = stack.pop()
                yield screen.get("id", "?"), state.get("name", state.get("id", "?")), node, anc
                kids = node.get("children")
                if isinstance(kids, list):
                    for kid in reversed(kids):
                        if isinstance(kid, dict):
                            stack.append((kid, anc + (node,)))


def _region(node, anc):
    return " > ".join(_label(n) for n in anc + (node,))


def _style(node):
    s = node.get("style")
    return s if isinstance(s, dict) else {}


def _kind(node):
    comp = node.get("component")
    return comp.get("kind") if isinstance(comp, dict) else None


def _variant(node):
    comp = node.get("component")
    return comp.get("variant") if isinstance(comp, dict) else None


def surface_color(manifest):
    for c in (manifest.get("tokens") or {}).get("colors") or []:
        if isinstance(c, dict) and str(c.get("name", "")).lower() in ("surface", "background"):
            h = norm_hex(c.get("hex"))
            if h:
                return h, "surface-token"
    return "#FFFFFF", "default-white"


def _background(node, anc, manifest):
    for i, n in enumerate((node,) + tuple(reversed(anc))):
        h = norm_hex(_style(n).get("background"))
        if h:
            return h, "node" if i == 0 else "ancestor"
    return surface_color(manifest)


def _disabled(node, anc):
    return any(_variant(n) == "disabled" for n in anc + (node,))


# ---------------------------------------------------------------- checks

def text_contrast(manifest):
    hits = []
    for screen, state, node, anc in iter_nodes(manifest):
        s = _style(node)
        fg = norm_hex(s.get("color"))
        if not fg or not isinstance(node.get("text"), str) or _disabled(node, anc):
            continue  # SC 1.4.3 exempts inactive (disabled) components
        bg, src = _background(node, anc, manifest)
        size, weight = _num(s.get("size")), _num(s.get("weight")) or 400
        large = size is not None and (size >= 24 or (size >= 18.66 and weight >= 700))
        need = 3.0 if large else 4.5
        ratio = contrast_ratio(fg, bg)
        if ratio < need:
            hits.append({"screen": screen, "state": state, "region": _region(node, anc),
                         "text": node["text"], "color": fg, "background": bg,
                         "background_source": src, "contrast_ratio": round(ratio, 2),
                         "required": need, "size": size, "weight": weight, "large_text": large})
    return hits


def border_contrast(manifest):
    hits = []
    for screen, state, node, anc in iter_nodes(manifest):
        kind = _kind(node)
        border = _style(node).get("border")
        if kind not in BORDERED_KINDS or not isinstance(border, dict) or _disabled(node, anc):
            continue
        bc = norm_hex(border.get("color"))
        if not bc or norm_hex(_style(node).get("background")):
            continue  # a filled component is identified by its fill, not its border
        # the border sits on whatever is behind the component: its parent's background
        bg, src = _background(anc[-1], anc[:-1], manifest) if anc else surface_color(manifest)
        ratio = contrast_ratio(bc, bg)
        if ratio < 3.0:
            hits.append({"screen": screen, "state": state, "region": _region(node, anc),
                         "kind": kind, "border": bc, "background": bg, "background_source": src,
                         "contrast_ratio": round(ratio, 2), "required": 3.0})
    return hits


def small_touch_targets(manifest, min_dp=48):
    """Interactive components whose measured height or width is under min_dp logical px.

    Height comes from style.height; for a link without one, from style.line_height
    (`measured_from` says which). Components with no measured size are skipped.
    """
    hits = []
    for screen, state, node, anc in iter_nodes(manifest):
        kind = _kind(node)
        if kind not in INTERACTIVE_KINDS:
            continue
        s = _style(node)
        height, source = _num(s.get("height")), "height"
        if height is None and kind == "link":
            height, source = _num(s.get("line_height")), "line_height"
        width = _num(s.get("width"))
        small = [d for d, v in (("height", height), ("width", width)) if v is not None and v < min_dp]
        if small:
            hits.append({"screen": screen, "state": state, "region": _region(node, anc),
                         "kind": kind, "variant": _variant(node), "text": node.get("text"),
                         "height": height, "width": width, "measured_from": source,
                         "too_small": small, "minimum": min_dp})
    return hits


def small_text(manifest, min_px=12):
    """Text-bearing nodes whose style.size is under min_px."""
    hits = []
    for screen, state, node, anc in iter_nodes(manifest):
        size = _num(_style(node).get("size"))
        if size is not None and size < min_px and isinstance(node.get("text"), str):
            hits.append({"screen": screen, "state": state, "region": _region(node, anc),
                         "text": node["text"], "size": size, "minimum": min_px})
    return hits


def _screen_kinds(screen):
    kinds = set()
    for state in screen.get("states") or []:
        if isinstance(state, dict) and isinstance(state.get("layout"), dict):
            for _, _, node, _ in iter_nodes({"screens": [{"id": "", "states": [state]}]}):
                k = _kind(node)
                if k:
                    kinds.add(k)
                kids = node.get("children") if isinstance(node.get("children"), list) else []
                if sum(1 for c in kids if isinstance(c, dict) and _kind(c) == "card") >= 3:
                    kinds.add("card-list")
    return kinds


def missing_states(manifest):
    """{screen id: [missing state names]} for screens with inputs or lists.

    Inputs (text-field, checkbox, radio, switch) expect loading + error; lists
    (a list-item, or a container with 3+ cards) expect empty + loading. Other
    screens expect nothing. `dark` is never expected (a product decision).
    """
    out = {}
    for screen in manifest.get("screens") or []:
        if not isinstance(screen, dict):
            continue
        kinds = _screen_kinds(screen)
        expected = set()
        if kinds & INPUT_KINDS:
            expected |= {"loading", "error"}
        if kinds & {"list-item", "card-list"}:
            expected |= {"empty", "loading"}
        have = {s.get("name") for s in screen.get("states") or [] if isinstance(s, dict)}
        missing = [n for n in ("loading", "empty", "error") if n in expected and n not in have]
        if missing:
            out[screen.get("id", "?")] = missing
    return out


def _grid_values(manifest):
    """(value, kind, screen, state, region) for every padding side, gap and non-pill radius."""
    for screen, state, node, anc in iter_nodes(manifest):
        s = _style(node)
        pad = s.get("padding")
        sides = pad if isinstance(pad, list) else [pad]
        for v in sides:
            if _num(v) is not None:
                yield v, "padding", screen, state, _region(node, anc)
        if _num(s.get("gap")) is not None:
            yield s["gap"], "gap", screen, state, _region(node, anc)
        r, h = _num(s.get("radius")), _num(s.get("height"))
        if r is not None and not (h is not None and r >= h / 2 - 0.5):  # pills are exempt
            yield r, "radius", screen, state, _region(node, anc)
    tokens = manifest.get("tokens") or {}
    for key, kind in (("spacing", "spacing token"), ("radii", "radius token")):
        for v in tokens.get(key) or []:
            if _num(v) is not None:
                yield v, kind, "all", None, f"tokens.{key}"


def _layout_colors(manifest):
    counts = {}
    for c in (manifest.get("tokens") or {}).get("colors") or []:
        h = norm_hex(c.get("hex")) if isinstance(c, dict) else None
        if h:
            counts.setdefault(h, 0)
    for _, _, node, _ in iter_nodes(manifest):
        s = _style(node)
        border = s.get("border") if isinstance(s.get("border"), dict) else {}
        for v in (s.get("color"), s.get("background"), border.get("color")):
            h = norm_hex(v)
            if h:
                counts[h] = counts.get(h, 0) + 1
    return counts


# ---------------------------------------------------------------- audit

def _merge(raw, key_fields):
    """Merge identical findings across states of one screen: keep the first, list the rest."""
    merged, index = [], {}
    for f in raw:
        key = (f["screen"],) + tuple(json.dumps(f.get(k), sort_keys=True) for k in key_fields)
        if key in index:
            first = index[key]
            if f.get("state") and f["state"] != first.get("state") and f["state"] not in first.setdefault("also_in", []):
                first["also_in"].append(f["state"])
            continue
        index[key] = f
        merged.append(f)
    return merged


def _finding(category, severity, screen, state, region, detail, measured, guideline):
    f = {"category": category, "severity": severity, "screen": screen}
    if state:
        f["state"] = state
    if region:
        f["region"] = region
    f.update({"detail": detail, "measured": measured, "guideline": guideline})
    return f


def audit(manifest, grid=4):
    raw = []
    for h in text_contrast(manifest):
        sev = "high" if h["contrast_ratio"] < 3.0 else "medium"
        measured = {k: h[k] for k in ("text", "color", "background", "background_source",
                                       "contrast_ratio", "required", "size", "weight", "large_text")}
        raw.append(_finding("accessibility", sev, h["screen"], h["state"], h["region"],
                            f'Text "{h["text"]}" {h["color"]} on {h["background"]} has contrast '
                            f'{h["contrast_ratio"]}:1, below the {h["required"]}:1 AA minimum.',
                            measured, G_CONTRAST))
    for h in border_contrast(manifest):
        measured = {k: h[k] for k in ("kind", "border", "background", "background_source",
                                       "contrast_ratio", "required")}
        raw.append(_finding("accessibility", "medium", h["screen"], h["state"], h["region"],
                            f'{h["kind"]} border {h["border"]} on {h["background"]} has contrast '
                            f'{h["contrast_ratio"]}:1, below 3:1 for component boundaries.',
                            measured, G_NONTEXT))
    for h in small_touch_targets(manifest):
        smallest = min(v for v in (h["height"], h["width"]) if v is not None and v < h["minimum"])
        sev = "high" if smallest < 24 else "medium" if smallest < 44 else "low"
        measured = {k: h[k] for k in ("kind", "variant", "text", "height", "width",
                                       "measured_from", "too_small", "minimum")}
        dims = ", ".join(f"{d} {h[d]} px" for d in h["too_small"])
        raw.append(_finding("accessibility", sev, h["screen"], h["state"], h["region"],
                            f'{h["kind"]} "{h["text"] or ""}" has a touch target of {dims}, '
                            f'under {h["minimum"]} px.', measured, G_TARGET))
    for h in small_text(manifest):
        sev = "medium" if h["size"] < 11 else "low"
        raw.append(_finding("accessibility", sev, h["screen"], h["state"], h["region"],
                            f'Text "{h["text"]}" is {h["size"]} px, under {h["minimum"]} px.',
                            {"text": h["text"], "size": h["size"], "minimum": h["minimum"]},
                            G_SMALL_TEXT))
    counts = _layout_colors(manifest)
    for a, b, d in near_duplicate_colors(counts):
        raw.append(_finding("consistency", "low", "all", None, None,
                            f"Colors {a} and {b} differ by delta E {d}; they read as one color.",
                            {"color_a": a, "color_b": b, "delta_e": d, "threshold": 3.0,
                             "uses_a": counts[a], "uses_b": counts[b]}, G_DUP_COLOR))
    by_value = {}
    for v, kind, screen, state, region in _grid_values(manifest):
        if _off_grid(v, grid):
            by_value.setdefault((v, screen), []).append((kind, state, region))
    for (v, screen), where in sorted(by_value.items(), key=lambda x: (x[0][1], x[0][0])):
        nearest = round(v / grid) * grid
        kinds = sorted({k for k, _, _ in where})
        states = sorted({s for _, s, _ in where if s})
        raw.append(_finding("consistency", "low", screen, states[0] if states else None,
                            where[0][2],
                            f"{'/'.join(kinds)} value {v} px is off the {grid}-pt grid "
                            f"(nearest {nearest} px), used {len(where)} time(s).",
                            {"value": v, "grid": grid, "nearest_on_grid": nearest,
                             "kinds": kinds, "occurrences": len(where),
                             "regions": sorted({r for _, _, r in where})[:5]}, G_GRID))
    for screen, missing in missing_states(manifest).items():
        have = []
        for s in manifest.get("screens") or []:
            if isinstance(s, dict) and s.get("id") == screen:
                have = [st.get("name") for st in s.get("states") or [] if isinstance(st, dict)]
        raw.append(_finding("states", "medium", screen, None, None,
                            f"Screen {screen} has no {', '.join(missing)} state.",
                            {"missing": missing, "present": have}, G_STATES))

    raw = _merge(raw, ["detail"])
    raw.sort(key=lambda f: (SEVERITIES.index(f["severity"]), CATEGORIES.index(f["category"]),
                            f["screen"]))
    counters = {}
    findings = []
    for f in raw:
        counters[f["category"]] = counters.get(f["category"], 0) + 1
        findings.append({"id": f"audit-{f['category']}-{counters[f['category']]}", **f})
    summary = {s: sum(1 for f in findings if f["severity"] == s) for s in SEVERITIES}
    return findings, summary


def load_manifest(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ManifestError(f"cannot read manifest {path}: {e}")
    if not isinstance(data, dict) or not isinstance(data.get("screens"), list):
        raise ManifestError(f"invalid manifest {path}: expected an object with a screens list")
    return data


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="design_audit.py",
        description="Measure contrast, touch targets, small text, near-duplicate colors, "
                    "off-grid spacing and missing states in a Sauces manifest; write "
                    "design-audit.json. Exit 0 when written (findings are not failures), "
                    "2 on usage error or unreadable/invalid manifest.",
    )
    ap.add_argument("--manifest", required=True, help="path to .sauces/manifest.json")
    ap.add_argument("-o", "--output", help="output path (default: design-audit.json beside the manifest)")
    ap.add_argument("--grid", type=int, default=4, help="spacing grid in logical px (default 4)")
    args = ap.parse_args(argv)
    if args.grid < 1:
        ap.error("--grid must be a positive integer")
    try:
        manifest = load_manifest(args.manifest)
    except ManifestError as e:
        print(str(e), file=sys.stderr)
        return 2
    findings, summary = audit(manifest, grid=args.grid)
    out = Path(args.output) if args.output else Path(args.manifest).parent / "design-audit.json"
    doc = {
        "version": 1,
        "about": ("Measured design facts from design_audit.py. Each finding cites a guideline "
                  "and carries the measured numbers; the plan turns them into design "
                  "suggestions the user keeps or applies. Sizes are logical px. screen 'all' "
                  "means manifest-wide (tokens)."),
        "manifest": str(args.manifest),
        "grid": args.grid,
        "summary": summary,
        "findings": findings,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"{len(findings)} findings ({summary['high']} high, {summary['medium']} medium, "
          f"{summary['low']} low) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
