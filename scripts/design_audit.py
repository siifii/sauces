#!/usr/bin/env python3
"""Measure design facts in .sauces/manifest.json and write .sauces/design-audit.json (Sauces).

Stdlib only. Reads the manifest's tokens and every state's `layout` tree (logical
px) and measures, without judging taste:

  accessibility  text contrast (WCAG 2.2 SC 1.4.3), UI-component border contrast
                 (SC 1.4.11), touch targets of interactive elements (Material
                 48 x 48 dp, HIG 44 x 44 pt, WCAG SC 2.5.8 24 x 24 with its spacing
                 exception), text under 12 px
  consistency    near-duplicate colors (CIE76 delta E < 3), spacing and radius
                 values off the 4-pt grid, more than 3 corner radii, more than 6
                 text styles on a screen or sizes off the platform type scales
  states         missing loading / empty / error states (screens with inputs
                 expect loading + error, screens with lists expect empty + loading)

Each finding: {id: audit-<category>-<n>, category, severity: high|medium|low,
screen, state?, also_in?, region?, detail, measured: {...numbers...}, guideline}.
`also_in` lists the other places with the same finding as "<screen>/<state>".
Findings are facts for the plan skill to turn into design suggestions; they are
not failures. They are sorted by severity, then category in the order
accessibility, ux, states, localization, platform, consistency.

Text contrast pairs a text's color (its own `style.color`, or for a text node the
nearest ancestor's) with the background of the nearest node (itself, then
ancestors) that has `style.background`; with none, the color token named
surface/background, else #FFFFFF. Colors with alpha (#RRGGBBAA) are composited
onto what is behind them. `measured.background_source` says where the background
came from.

Exit codes: 0 audit written (findings or not), 2 usage error or an unreadable /
invalid manifest.
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

CATEGORIES = ["accessibility", "ux", "states", "localization", "platform", "consistency"]
SEVERITIES = ["high", "medium", "low"]

INTERACTIVE_KINDS = {"button", "icon-button", "toggle", "link", "text-field", "checkbox",
                     "radio", "switch", "chip", "list-item"}
INPUT_KINDS = {"text-field", "checkbox", "radio", "switch"}
BORDERED_KINDS = {"text-field", "checkbox", "radio", "switch", "chip", "button"}

# Default type sizes: Material 3 type scale (display L..label S) and Apple HIG Dynamic
# Type styles at the default (Large) size, iOS.
M3_TYPE_SIZES = {57, 45, 36, 32, 28, 24, 22, 16, 14, 12, 11}
HIG_TYPE_SIZES = {34, 28, 22, 20, 17, 16, 15, 13, 12, 11}
MAX_RADII = 3
MAX_TEXT_STYLES = 6

G_CONTRAST = ("WCAG 2.2 SC 1.4.3 Contrast (Minimum), level AA: 4.5:1 for normal text, "
              "3:1 for large text (>= 24 px, or >= 18.66 px bold)")
G_NONTEXT = ("WCAG 2.2 SC 1.4.11 Non-text Contrast, level AA: 3:1 for the visual boundary "
             "that identifies a UI component against adjacent colors")
G_TARGET = ("Material 3 accessibility: touch targets at least 48 x 48 dp; Apple HIG: at least "
            "44 x 44 pt. WCAG 2.2 SC 2.5.8 Target Size (Minimum), level AA: 24 x 24 CSS px, "
            "unless a 24 px circle centered on each undersized target does not intersect "
            "another target or its circle (spacing exception), or the target is an inline "
            "link in a sentence, among other exceptions")
G_SMALL_TEXT = ("Legibility recommendation, not a WCAG requirement: Material 3's smallest type "
                "role (label small) is 11 sp and body text starts at 12 sp; Apple HIG's "
                "smallest default text style (caption 2) is 11 pt. Text under 12 px is hard to "
                "read for many users; whatever the size, it must scale with the system text "
                "size (WCAG 2.2 SC 1.4.4 Resize Text)")
G_DUP_COLOR = ("Common design-token practice: colors within CIE76 delta E 3 are hard to tell "
               "apart and usually mean one intended color; Material 3 assigns each purpose "
               "one color role")
G_GRID = ("Material Design spacing: a 4 dp grid for small elements and an 8 dp baseline grid "
          "for layout. A 4-pt spacing grid is also common practice on iOS (a convention, not "
          "an Apple HIG rule). Off-grid values usually mean a measurement or intent gap")
G_RADII = ("Material 3 shape scale: a small set of corner radii (none 0, extra small 4, small "
           "8, medium 12, large 16, extra large 28 dp, full) reused by role. Using more than "
           f"{MAX_RADII} distinct radii in one design is a consistency smell (common practice)")
G_TYPE = ("Material 3 type scale: 15 roles (display, headline, title, body, label in large, "
          "medium, small) with fixed sizes; on iOS, Apple HIG Dynamic Type text styles (large "
          "title 34 ... caption 2 11 pt). Using more than "
          f"{MAX_TEXT_STYLES} size/weight styles on one screen, or sizes on neither scale, "
          "suggests type-scale sprawl (common practice)")
G_STATES = ("Common UX practice (Nielsen heuristics 1, visibility of system status, and 9, help "
            "users recognize, diagnose and recover from errors): show progress while waiting "
            "(loading), explain what failed and how to recover (error), and say why a list is "
            "empty and what to do (empty)")


class ManifestError(Exception):
    pass


# ---------------------------------------------------------------- colors

def parse_rgba(value):
    """'#RRGGBB', '#RRGGBBAA' or '#RGB' -> (r, g, b, alpha 0..1), else None."""
    if not isinstance(value, str):
        return None
    m = re.fullmatch(r"#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", value.strip())
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    alpha = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)


def parse_hex(value):
    """'#RRGGBB', '#RRGGBBAA' or '#RGB' -> (r, g, b) ints (alpha dropped), else None."""
    rgba = parse_rgba(value)
    return rgba[:3] if rgba else None


def norm_hex(value):
    """Uppercase '#RRGGBB', or '#RRGGBBAA' when not fully opaque; None if not a color."""
    rgba = parse_rgba(value)
    if not rgba:
        return None
    if rgba[3] < 1.0:
        return "#%02X%02X%02X%02X" % (rgba[0], rgba[1], rgba[2], round(rgba[3] * 255))
    return "#%02X%02X%02X" % rgba[:3]


def composite(fg, bg):
    """Alpha-composite color fg (may carry alpha) over bg; returns opaque '#RRGGBB'."""
    f, b = parse_rgba(fg), parse_rgba(bg)
    if f is None or b is None:
        raise ValueError(f"not hex colors: {fg!r}, {bg!r}")
    a = f[3]
    return "#%02X%02X%02X" % tuple(round(a * f[i] + (1 - a) * b[i]) for i in range(3))


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
    """WCAG 2.x contrast ratio between two hex colors (1.0 .. 21.0).

    A translucent fg (#RRGGBBAA) is composited onto bg first; bg is taken as opaque.
    """
    if parse_rgba(fg) and parse_rgba(fg)[3] < 1.0:
        fg = composite(fg, bg)
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
    """CIE76 delta E between two sRGB hex colors (D65; alpha ignored)."""
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
            h = parse_hex(c.get("hex"))
            if h:
                return "#%02X%02X%02X" % h, "surface-token"
    return "#FFFFFF", "default-white"


def _background(node, anc, manifest):
    """Opaque background behind node: nearest style.background, translucent layers composited."""
    layers = []
    for i, n in enumerate((node,) + tuple(reversed(anc))):
        rgba = parse_rgba(_style(n).get("background"))
        if rgba:
            layers.append((_style(n)["background"], i))
            if rgba[3] >= 1.0:
                break
    if layers and parse_rgba(layers[-1][0])[3] >= 1.0:
        base, src = norm_hex(layers[-1][0]), "node" if layers[0][1] == 0 else "ancestor"
        layers = layers[:-1]
    else:
        base, src = surface_color(manifest)
        if layers:
            src = "node" if layers[0][1] == 0 else "ancestor"
    for color, _ in reversed(layers):
        base = composite(color, base)
    return base, src


def _disabled(node, anc):
    return any(_variant(n) == "disabled" for n in anc + (node,))


def _text_color(node, anc):
    """The node's own style.color; a text node inherits the nearest ancestor's."""
    own = _style(node).get("color")
    if parse_rgba(own):
        return norm_hex(own)
    if node.get("type") == "text":
        for n in reversed(anc):
            c = _style(n).get("color")
            if parse_rgba(c):
                return norm_hex(c)
    return None


# ---------------------------------------------------------------- checks

def text_contrast(manifest):
    hits = []
    for screen, state, node, anc in iter_nodes(manifest):
        s = _style(node)
        fg = _text_color(node, anc)
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


def _is_target(node, anc):
    """Interactive components, plus icons that lead or trail a text field (e.g. a password toggle)."""
    kind = _kind(node)
    if kind in INTERACTIVE_KINDS:
        return True
    return kind == "icon" and bool(anc) and _kind(anc[-1]) == "text-field"


def _target_height(node):
    s = _style(node)
    h = _num(s.get("height"))
    if h is None and _kind(node) == "link":
        return _num(s.get("line_height")), "line_height"
    return h, "height"


def _wcag_spacing(node, anc):
    """'fails' | 'passes' | 'unknown': WCAG 2.5.8 spacing between node and adjacent targets.

    Only judged inside a row/column with a numeric gap: along that axis, each undersized
    target's 24 px circle extends max(0, 12 - size/2) beyond its box; adjacent targets fail
    when the two extensions exceed the gap.
    """
    if not anc:
        return "unknown"
    parent = anc[-1]
    axis = {"row": "width", "column": "height"}.get(parent.get("type"))
    gap = _num(_style(parent).get("gap"))
    kids = parent.get("children") if isinstance(parent.get("children"), list) else []
    idx = next((i for i, k in enumerate(kids) if k is node), None)
    if axis is None or gap is None or idx is None:
        return "unknown"

    def size(n):
        if axis == "height":
            return _target_height(n)[0]
        w = _style(n).get("width")
        return float("inf") if w == "fill" else _num(w)

    mine = size(node)
    if mine is None:
        return "unknown"
    ext = max(0.0, 12 - mine / 2)
    verdict = "passes"
    for j in (idx - 1, idx + 1):
        if not 0 <= j < len(kids) or not isinstance(kids[j], dict):
            continue
        other = kids[j]
        if not _is_target(other, anc):
            continue
        theirs = size(other)
        if theirs is None:
            verdict = "unknown"
            continue
        if ext + max(0.0, 12 - theirs / 2) > gap:
            return "fails"
    return verdict


def small_touch_targets(manifest, min_dp=48):
    """Interactive elements whose measured height or width is under min_dp logical px.

    Height comes from style.height; for a link without one, from style.line_height
    (`measured_from` says which). Elements with no measured size are skipped.
    `wcag_spacing` is the 2.5.8 spacing verdict: fails | passes | unknown.
    """
    hits = []
    for screen, state, node, anc in iter_nodes(manifest):
        if not _is_target(node, anc):
            continue
        height, source = _target_height(node)
        width = _num(_style(node).get("width"))
        small = [d for d, v in (("height", height), ("width", width)) if v is not None and v < min_dp]
        if small:
            hits.append({"screen": screen, "state": state, "region": _region(node, anc),
                         "kind": _kind(node), "variant": _variant(node),
                         "text": node.get("text") or node.get("description"),
                         "height": height, "width": width, "measured_from": source,
                         "too_small": small, "minimum": min_dp,
                         "wcag_spacing": _wcag_spacing(node, anc)})
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


def _is_pill(style):
    r, h, w = _num(style.get("radius")), _num(style.get("height")), _num(style.get("width"))
    short = min(v for v in (h, w) if v is not None) if (h is not None or w is not None) else None
    return r is not None and short is not None and r >= short / 2 - 0.5


def mixed_radii(manifest, max_count=MAX_RADII):
    """Distinct corner radii (rounded to 1 px, excluding 0 and pills) when there are more than max_count."""
    seen = {}
    for screen, state, node, anc in iter_nodes(manifest):
        s = _style(node)
        r = _num(s.get("radius"))
        if r is None or _is_pill(s) or round(r) == 0:
            continue
        seen.setdefault(round(r), f"{screen}/{state}")
    for v in (manifest.get("tokens") or {}).get("radii") or []:
        if _num(v) is not None and round(v) != 0:
            seen.setdefault(round(v), "tokens")
    if len(seen) <= max_count:
        return None
    return {"radii": sorted(seen), "count": len(seen), "maximum": max_count}


def _on_scale(size):
    return any(abs(size - s) <= 0.5 for s in M3_TYPE_SIZES | HIG_TYPE_SIZES)


def type_sprawl(manifest, max_styles=MAX_TEXT_STYLES):
    """{screen: {styles, count, off_scale_sizes}} for screens with more than max_styles
    size x weight text styles, or two or more sizes on neither the M3 nor the HIG scale."""
    styles = {}
    for screen, state, node, anc in iter_nodes(manifest):
        s = _style(node)
        size = _num(s.get("size"))
        if size is None or not isinstance(node.get("text"), str):
            continue
        styles.setdefault(screen, set()).add((size, _num(s.get("weight")) or 400))
    out = {}
    for screen, st in styles.items():
        off = sorted({sz for sz, _ in st if not _on_scale(sz)})
        if len(st) > max_styles or len(off) >= 2:
            out[screen] = {"styles": [f"{sz:g}/{w:g}" for sz, w in sorted(st)], "count": len(st),
                           "maximum": max_styles, "off_scale_sizes": off}
    return out


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
    """(value, kind, place, region) for every padding side, gap and non-pill radius."""
    for screen, state, node, anc in iter_nodes(manifest):
        s = _style(node)
        place = f"{screen}/{state}"
        pad = s.get("padding")
        sides = pad if isinstance(pad, list) else [pad]
        for v in sides:
            if _num(v) is not None:
                yield v, "padding", place, _region(node, anc)
        if _num(s.get("gap")) is not None:
            yield s["gap"], "gap", place, _region(node, anc)
        if _num(s.get("radius")) is not None and not _is_pill(s):
            yield s["radius"], "radius", place, _region(node, anc)
    tokens = manifest.get("tokens") or {}
    for key, kind in (("spacing", "spacing token"), ("radii", "radius token")):
        for v in tokens.get(key) or []:
            if _num(v) is not None:
                yield v, kind, "tokens", f"tokens.{key}"


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

def _merge(raw):
    """Merge identical findings (same screen and detail) across states: keep the first,
    list the other places in also_in as <screen>/<state>."""
    merged, index = [], {}
    for f in raw:
        key = (f["screen"], f["detail"])
        if key in index:
            first = index[key]
            place = f"{f['screen']}/{f.get('state')}"
            if f.get("state") and f["state"] != first.get("state") and place not in first.setdefault("also_in", []):
                first["also_in"].append(place)
            continue
        index[key] = f
        merged.append(f)
    return merged


def _finding(category, severity, screen, state, region, detail, measured, guideline, also_in=None):
    f = {"category": category, "severity": severity, "screen": screen}
    if state:
        f["state"] = state
    if also_in:
        f["also_in"] = also_in
    if region:
        f["region"] = region
    f.update({"detail": detail, "measured": measured, "guideline": guideline})
    return f


def _target_severity(h):
    smallest = min(v for v in (h["height"], h["width"]) if v is not None and v < h["minimum"])
    if smallest < 24 and h["wcag_spacing"] == "fails":
        return "high", smallest
    if smallest < 44:
        return "medium", smallest
    return "low", smallest


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
        sev, smallest = _target_severity(h)
        measured = {k: h[k] for k in ("kind", "variant", "text", "height", "width",
                                       "measured_from", "too_small", "minimum", "wcag_spacing")}
        dims = ", ".join(f"{d} {h[d]} px" for d in h["too_small"])
        if smallest >= 24:
            wcag = "meets the WCAG 2.5.8 24 px minimum"
        elif h["wcag_spacing"] == "fails":
            wcag = "fails WCAG 2.5.8 (under 24 px and too close to an adjacent target)"
        elif h["wcag_spacing"] == "passes":
            wcag = "passes WCAG 2.5.8 by its spacing exception"
        else:
            wcag = "spacing unknown, likely passes WCAG 2.5.8 by its spacing exception"
        raw.append(_finding("accessibility", sev, h["screen"], h["state"], h["region"],
                            f'{h["kind"]} "{h["text"] or ""}" has a touch target of {dims}: '
                            f'under Material 48 dp and HIG 44 pt; {wcag}.', measured, G_TARGET))
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
    for v, kind, place, region in _grid_values(manifest):
        if _off_grid(v, grid):
            by_value.setdefault(v, []).append((kind, place, region))
    for v, where in sorted(by_value.items()):
        nearest = round(v / grid) * grid
        kinds = sorted({k for k, _, _ in where})
        places = list(dict.fromkeys(p for _, p, _ in where))
        first = places[0]
        screen, state = first.split("/", 1) if "/" in first else ("all", None)
        raw.append(_finding("consistency", "low", screen, state, where[0][2],
                            f"{'/'.join(kinds)} value {v} px is off the {grid}-pt grid "
                            f"(nearest {nearest} px), used {len(where)} time(s).",
                            {"value": v, "grid": grid, "nearest_on_grid": nearest,
                             "kinds": kinds, "occurrences": len(where),
                             "regions": sorted({r for _, _, r in where})[:5]}, G_GRID,
                            also_in=places[1:]))
    radii = mixed_radii(manifest)
    if radii:
        raw.append(_finding("consistency", "low", "all", None, None,
                            f"The design uses {radii['count']} corner radii "
                            f"({', '.join(map(str, radii['radii']))} px), more than {MAX_RADII}.",
                            radii, G_RADII))
    for screen, t in type_sprawl(manifest).items():
        extra = (f"; sizes {', '.join(f'{s:g}' for s in t['off_scale_sizes'])} px are on neither "
                 "the Material 3 nor the HIG scale") if t["off_scale_sizes"] else ""
        raw.append(_finding("consistency", "low", screen, None, None,
                            f"Screen {screen} uses {t['count']} text styles (size/weight){extra}.",
                            t, G_TYPE))
    for screen, missing in missing_states(manifest).items():
        have = []
        for s in manifest.get("screens") or []:
            if isinstance(s, dict) and s.get("id") == screen:
                have = [st.get("name") for st in s.get("states") or [] if isinstance(st, dict)]
        raw.append(_finding("states", "medium", screen, None, None,
                            f"Screen {screen} has no {', '.join(missing)} state.",
                            {"missing": missing, "present": have}, G_STATES))

    raw = _merge(raw)
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
                    "off-grid spacing, mixed radii, type-scale sprawl and missing states in a "
                    "Sauces manifest; write design-audit.json. Exit 0 when written (findings "
                    "are not failures), 2 on usage error or unreadable/invalid manifest.",
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
                  "means manifest-wide (tokens or the whole design). also_in lists other "
                  "places with the same finding as <screen>/<state> ('tokens' for token "
                  "values). Sorted by severity, then category: accessibility, ux, states, "
                  "localization, platform, consistency."),
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
