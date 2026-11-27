#!/usr/bin/env python3
"""Render the Sauces report.html from the pipeline's .sauces/ working state.

Fills skills/report/assets/report-template.html with the manifest, project
profile, plan, design audit, build outputs (todos, deviations, state) and
verify results. The page is self-contained and makes no network requests: inline
CSS, screenshots embedded as data URIs, the component graph as inline SVG with
its source as plain text. `--allow-cdn` additionally loads mermaid from a CDN
(exact pinned version, SRI hash) for a richer graph; it is off by default.

A missing input makes its section say "not run"; an unreadable or wrong-shaped one
is listed under "Unreadable inputs". All text from the inputs is HTML-escaped.

Exit codes: 0 written, 2 usage error (missing .sauces dir or template),
3 missing dependency.
"""
import argparse
import base64
import io
import json
import re
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path

DEFAULT_TEMPLATE = Path(__file__).resolve().parent.parent / "skills" / "report" / "assets" / "report-template.html"
THUMB_WIDTH = 240
LEVELS = ("token", "atom", "molecule", "organism", "screen")
DECISIONS = ("reuse", "extend", "new", "token")
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
RTL_LOCALES = {"ar", "he", "fa", "ur", "iw", "ps", "sd", "ug", "yi", "dv", "ckb"}

# Pinned for --allow-cdn only. The hash is the SRI sha384 of that exact file.
MERMAID_VERSION = "11.4.1"
MERMAID_SRI = "sha384-rbtjAdnIQE/aQJGEgXrVUlMibdfTSa4PQju4HDhN3sR2PmaKFzhEafuePsl9H/9I"

# Practices the build references ask for, as (evidence key, text). The report never claims a
# practice was followed on its own: each one is ticked, flagged or "not checked" from the
# run's evidence (see practice_checks).
PRACTICES = {
    "flutter": [
        ("tokens", "Colors and type come from the theme (ColorScheme, TextTheme, ThemeExtension), never Colors.* or hex literals."),
        ("strings", "Every user-facing string lives in the localization files of every locale; non-source locales are marked for translation."),
        ("rtl", "Directional layout (EdgeInsetsDirectional, AlignmentDirectional) so right-to-left locales mirror correctly."),
        ("extend", "Existing components are extended with optional parameters whose defaults keep today's behavior."),
        ("states", "Each screen state can be shown by seeding its state class, which is how tests and verify render it."),
        ("a11y", "Touch targets of at least 48 dp, semantics labels from l10n, and no fixed-height text containers."),
        ("todos", "Unknown behavior (API calls, navigation) is a TODO(sauces) comment, never a fake."),
    ],
}
GENERIC_PRACTICES = [
    ("tokens", "Design values come from the project's tokens and theme, not literals."),
    ("strings", "User-facing strings live in the project's string resources."),
    ("extend", "Existing components are extended, never silently replaced."),
]


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
        prog="report_render.py",
        description="Build report.html from the .sauces/ working state. Missing inputs make "
                    "their section say 'not run'. Exit 0 written, 2 usage error, 3 missing dependency.",
    )
    p.add_argument("--sauces-dir", default=".sauces", help="path to the .sauces/ folder (default: .sauces)")
    p.add_argument("--template", help="HTML template (default: the plugin's report-template.html)")
    p.add_argument("-o", "--output", help="output file (default: <sauces-dir>/report.html)")
    p.add_argument("--allow-cdn", action="store_true",
                   help="also load mermaid from jsdelivr (pinned version + SRI) for a richer graph; "
                        "off by default so the report makes no network requests")
    return p.parse_args(argv)


# ---------- helpers ----------

def e(value) -> str:
    return escape("" if value is None else str(value), quote=True)


class Inputs:
    """The .sauces/ files, loaded once. A missing file is None; an unreadable one is None
    and listed in `problems`."""

    def __init__(self, sauces: Path):
        self.dir = sauces
        self.root = sauces.parent
        self.problems = []
        self.manifest = self._load("manifest.json", dict)
        self.profile = self._load("project-profile.json", dict)
        self.plan = self._load("plan.json", dict)
        self.audit = self._load("design-audit.json", dict)
        self.state = self._load("state.json", dict)
        self.todos = self._load("todos.json", list)
        self.deviations = self._load("deviations.json", list)
        self.verify = self._load("verify/summary.json", dict)
        self.lint = self._load("lint.json", dict)
        plan_md = sauces / "plan.md"
        self.plan_md = plan_md.read_text(encoding="utf-8", errors="replace") if plan_md.is_file() else None

    def _load(self, name, kind):
        path = self.dir / name
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            self.problems.append(f"{name}: {exc}")
            return None
        if not isinstance(data, kind):
            self.problems.append(f"{name}: expected a JSON {'object' if kind is dict else 'array'}, "
                                 f"found {type(data).__name__}")
            return None
        return data

    def resolve(self, rel):
        """A project-relative path from a .sauces/ file. `.sauces/...` maps into this folder,
        whatever it is called, so a copied or renamed .sauces/ still finds its images."""
        rel = str(rel or "")
        if rel.startswith(".sauces/"):
            return self.dir / rel[len(".sauces/"):]
        return self.root / rel

    def project(self):
        if not isinstance(self.profile, dict):
            return None
        projects = list_of(self.profile.get("projects"))
        plan = self.plan or {}
        platform = plan.get("platform")
        if not platform:
            return projects[0] if projects else None
        root = plan.get("project_root")
        matches = [project for project in projects if project.get("platform") == platform
                   and (root is None or project.get("root") == root)]
        return matches[0] if len(matches) == 1 else None

    def platform(self):
        if isinstance(self.plan, dict) and self.plan.get("platform"):
            return self.plan["platform"]
        proj = self.project()
        return proj.get("platform") if proj else None

    def gitignores_verify(self):
        """True when <root>/.gitignore already ignores .sauces/ or .sauces/verify/."""
        try:
            lines = (self.root / ".gitignore").read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return False
        return any(l.strip().strip("/") in (".sauces", ".sauces/verify", ".sauces/*") for l in lines)


def not_run(what: str, stage: str) -> str:
    return f'<p class="empty">not run: {e(what)} is missing. Run <code>/sauces:{e(stage)}</code> to fill this section.</p>'


def badge(text, kind=None) -> str:
    cls = f"badge b-{kind}" if kind else "badge"
    return f'<span class="{cls}">{e(text)}</span>'


def card(num, label, accent=False) -> str:
    cls = "card accent" if accent else "card"
    return f'<div class="{cls}"><div class="num">{e(num)}</div><div class="label">{e(label)}</div></div>'


def table(headers, rows) -> str:
    head = "".join(f"<th>{e(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def is_hex(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?", value) is not None


def chip(hex_color) -> str:
    if not is_hex(hex_color):
        return ""
    return f'<span class="chip" style="background:{hex_color}"></span>'


def thumbnail(path: Path):
    """A PNG data URI of the image scaled to THUMB_WIDTH, or None if it can't be read."""
    from PIL import Image

    try:
        with Image.open(path) as img:
            img.load()
            img = img.convert("RGBA")
            if img.width > THUMB_WIDTH:
                img = img.resize((THUMB_WIDTH, max(1, round(img.height * THUMB_WIDTH / img.width))),
                                 Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
    except (OSError, ValueError):
        return None
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def figure(path: Path, caption: str) -> str:
    uri = thumbnail(path) if path.is_file() else None
    if uri is None:
        return f'<figure><p class="empty">{e(caption)} missing</p></figure>'
    return f'<figure><img src="{uri}" alt="{e(caption)}"><figcaption>{e(caption)}</figcaption></figure>'


def fmt_score(score) -> str:
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        return f"{score:g}"
    return "–"


def items(inputs):
    plan = inputs.plan if isinstance(inputs.plan, dict) else {}
    return [i for i in plan.get("items") or [] if isinstance(i, dict)]


def results(inputs):
    v = inputs.verify if isinstance(inputs.verify, dict) else {}
    return [r for r in v.get("results") or [] if isinstance(r, dict)]


def strings(inputs):
    plan = inputs.plan if isinstance(inputs.plan, dict) else {}
    return [s for s in plan.get("strings") or [] if isinstance(s, dict)]


def list_of(value):
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


DECISION_PRIORITY = ("extend", "new", "reuse", "token")


def component_decisions(inputs):
    """{decision: count} per distinct component (screens excluded). A component used several
    times counts once, under its strongest decision (extend > new > reuse)."""
    by_name = {}
    for i in items(inputs):
        if i.get("level") == "screen":
            continue
        by_name.setdefault(i.get("name"), set()).add(i.get("decision"))
    counts = {d: 0 for d in DECISIONS}
    for decisions in by_name.values():
        for d in DECISION_PRIORITY:
            if d in decisions:
                counts[d] += 1
                break
    return counts


def as_dict(value):
    return value if isinstance(value, dict) else {}


def string_list(value):
    return [str(v) for v in value] if isinstance(value, list) else []


def file_list(inputs, key):
    return string_list((inputs.state or {}).get(key))


def asset_landings(inputs):
    """{asset name: project path} for design assets whose file name shows up among the files
    Sauces generated or changed."""
    files = file_list(inputs, "generated_files") + file_list(inputs, "changed_files")
    out = {}
    for a in list_of((inputs.manifest or {}).get("assets")):
        base = Path(str(a.get("path", ""))).name
        for f in files:
            if base and Path(f).name == base:
                out[a.get("name")] = f
                break
    return out


# ---------- sections ----------

def section_summary(inputs) -> str:
    if inputs.manifest is None and inputs.plan is None:
        return not_run("manifest.json and plan.json", "cook")
    parts = []
    its = items(inputs)
    counts = component_decisions(inputs)
    screens = [i for i in its if i.get("level") == "screen"]
    res = [r for r in results(inputs) if r.get("rendered")]
    threshold = (inputs.verify or {}).get("threshold", 90) if isinstance(inputs.verify, dict) else 90
    reused = counts["reuse"] + counts["extend"]
    built = reused + counts["new"]
    cards = [
        card(len(screens) if inputs.plan else "–", "screens built", accent=True),
        card(counts["reuse"], "components reused"),
        card(counts["extend"], "components extended"),
        card(counts["new"], "new components"),
        card(f"{round(100 * reused / built)}%" if built else "–", "reuse rate"),
    ]
    if res:
        avg = sum(r.get("score") or 0 for r in res) / len(res)
        passed = sum(1 for r in res if r.get("passed"))
        cards.append(card(f"{avg:.1f}", f"mean fidelity ({passed}/{len(res)} ≥ {fmt_score(threshold)})"))
    else:
        cards.append(card("–", "fidelity (verify not run)"))
    if isinstance(inputs.todos, list):
        cards.append(card(len(inputs.todos), "TODOs"))
    parts.append('<div class="cards">' + "".join(cards) + "</div>")

    proj = inputs.project()
    if proj:
        loc = as_dict(proj.get("localization"))
        facts = [
            ("Platform", proj.get("platform")),
            ("Architecture", proj.get("architecture")),
            ("State management", proj.get("state_management")),
            ("Localization", f"{loc.get('system', '?')} · {', '.join(string_list(loc.get('locales'))) or 'no locales'}"),
            ("Mode", (inputs.profile or {}).get("mode")),
        ]
        parts.append(table(["Project", ""], [[e(k), e(v)] for k, v in facts if v]))

    if results(inputs):
        rows = []
        for r in results(inputs):
            if r.get("rendered"):
                status = badge("passed", "pass") if r.get("passed") else badge("below threshold", "fail")
            else:
                status = badge("not rendered", "fail")
            rows.append([f"<code>{e(r.get('id'))}</code>", f"<strong>{e(fmt_score(r.get('score')))}</strong>",
                         status, e(r.get("iterations", 0))])
        parts.append("<h3>Fidelity by state</h3>" + table(["State", "Score", "Result", "Iterations"], rows))

    if isinstance(inputs.manifest, dict):
        bad = [s for s in list_of(inputs.manifest.get("sources")) if s.get("status") == "unreadable"]
        if bad:
            lines = "".join(f"<li><code>{e(s.get('ref'))}</code>: {e(s.get('reason', 'unreadable'))}</li>" for s in bad)
            parts.append(f'<div class="callout bad"><strong>Sources that could not be read</strong><ul>{lines}</ul></div>')
    if inputs.problems:
        lines = "".join(f"<li>{e(p)}</li>" for p in inputs.problems)
        parts.append(f'<div class="callout bad"><strong>Unreadable inputs</strong><ul>{lines}</ul></div>')
    return "".join(parts)


def section_fidelity(inputs) -> str:
    if not isinstance(inputs.verify, dict):
        return not_run("verify/summary.json", "verify")
    threshold = inputs.verify.get("threshold", 90)
    shots = []
    for r in results(inputs):
        rid = str(r.get("id", ""))
        safe_id = rid if re.fullmatch(r"[A-Za-z0-9_-]+(?:@[0-9]+--[A-Za-z0-9_-]+)?", rid) else None
        devs = string_list(r.get("deviations"))
        if r.get("rendered") and safe_id:
            n = r.get("iterations") or 1
            it = inputs.dir / "verify" / safe_id / f"iter-{n}"
            ref = inputs.resolve(r.get("reference"))
            rtl_png = inputs.dir / "verify" / safe_id / "rtl.png"
            rtl_fig = figure(rtl_png, "RTL") if rtl_png.is_file() else ""
            images = ('<div class="triptych">' + figure(ref, "design") + figure(it / "rendered.png", "built")
                      + figure(it / "diff.png", "difference") + rtl_fig + "</div>")
            cls = "pass" if r.get("passed") else "fail"
            score = f'<span class="score {cls}">{e(fmt_score(r.get("score")))}</span>'
            history = " → ".join(fmt_score(s) for s in r.get("scores") or [])
            meta = f'<p class="muted">{e(n)} iteration(s){": " + e(history) if history else ""} · threshold {e(fmt_score(threshold))}</p>'
        else:
            images = '<p class="empty">Not rendered: compared by hand with the checklist in <code>.sauces/verify/checklist.md</code>.</p>'
            score = badge("not rendered", "fail")
            meta = ""
        notes = []
        notes += [f"Intentional deviation: <code>{e(d)}</code> (applied design suggestion, not fixed back)" for d in devs]
        notes += [e(x) for x in string_list(r.get("remaining"))]
        notes += [f"RTL: {e(x)}" for x in string_list(r.get("rtl_issues"))]
        note_html = "<ul>" + "".join(f"<li>{n}</li>" for n in notes) + "</ul>" if notes else ""
        shots.append(f'<article class="shot"><header><strong>{e(rid)}</strong>{score}</header>{meta}{images}{note_html}</article>')
    if not shots:
        return '<p class="empty">No screen states were verified.</p>'
    renderer = inputs.verify.get("renderer")
    lead = f'<p class="muted">Rendered with {e(renderer)}.</p>' if renderer else ""
    if inputs.verify.get("lite") is True:
        lead += ('<p><strong>Lite run:</strong> one fix round at most, no determinism check, '
                 'no pseudo-locale pass, and only the narrowest frame of each web screen. '
                 'Run <code>/sauces:cook</code> without <code>--lite</code> for a full check.</p>')
    return lead + breakpoints_table(inputs) + '<div class="shots">' + "".join(shots) + "</div>"


def breakpoints_table(inputs) -> str:
    """Web only: per screen base, each designed width with its default-state score, and plan
    breakpoints that have no design frame ("not designed, not verified")."""
    manifest = inputs.manifest if isinstance(inputs.manifest, dict) else {}
    screens = [s for s in manifest.get("screens") or []
               if isinstance(s, dict) and isinstance(s.get("breakpoint"), int)]
    if not screens:
        return ""
    by_id = {str(r.get("id")): r for r in results(inputs)}
    plan = inputs.plan if isinstance(inputs.plan, dict) else {}
    planned = sorted({b.get("min_width") for b in plan.get("breakpoints") or []
                      if isinstance(b, dict) and isinstance(b.get("min_width"), int)
                      and b.get("min_width") > 0})
    rows = []
    for base in sorted({str(s.get("base") or s.get("id")) for s in screens}):
        widths = sorted(s["breakpoint"] for s in screens if str(s.get("base") or s.get("id")) == base)
        for w in widths:
            r = by_id.get(f"{base}@{w}--default", {})
            if r.get("rendered"):
                cls = "pass" if r.get("passed") else "fail"
                cell = f'<span class="score {cls}">{e(fmt_score(r.get("score")))}</span>'
            else:
                cell = badge("not rendered", "fail")
            rows.append(f"<tr><td><code>{e(base)}</code></td><td>{w} px</td><td>designed</td><td>{cell}</td></tr>")
        for w in planned:
            if w not in widths:
                rows.append(f"<tr><td><code>{e(base)}</code></td><td>{w} px</td>"
                            f"<td>project breakpoint</td><td>not designed, not verified</td></tr>")
    return ('<h3>Breakpoints</h3><p class="muted">Default-state score at each designed width. '
            'Project breakpoints with no design frame are listed, not scored.</p>'
            '<table><thead><tr><th>Screen</th><th>Width</th><th>Source</th><th>Default state</th></tr></thead>'
            "<tbody>" + "".join(rows) + "</tbody></table>")


def section_design_system(inputs) -> str:
    if not isinstance(inputs.plan, dict):
        return not_run("plan.json", "plan")
    parts = []
    st = inputs.plan.get("structure")
    if isinstance(st, dict):
        label = {o.get("id"): o.get("label") for o in list_of(st.get("options"))}
        choice = st.get("choice")
        rec = " (recommended)" if choice == st.get("recommended") else f" (recommended: {st.get('recommended')})"
        parts.append(f"<p><strong>Structure:</strong> {e(label.get(choice) or choice)}{e(rec)}</p>")
        reasons = st.get("reasons") or []
        if reasons:
            parts.append('<ul>' + "".join(f"<li>{e(x)}</li>" for x in reasons) + "</ul>")
    by_layer = {}
    for i in items(inputs):
        by_layer.setdefault(i.get("layer") or i.get("level") or "other", []).append(i)
    if by_layer:
        rows = []
        for layer, its in by_layer.items():
            for i in its:
                rows.append([f"<code>{e(layer)}</code>", f"<strong>{e(i.get('name'))}</strong>",
                             badge(i.get("decision"), i.get("decision") if i.get("decision") in DECISIONS else None),
                             f"<code>{e(i.get('path'))}</code>", e(i.get("design_ref")),
                             e(f"{round(100 * i['confidence'])}%" if isinstance(i.get("confidence"), (int, float)) else "")])
        parts.append("<h3>Components by layer</h3>" + table(["Layer", "Component", "Decision", "File", "Design element", "Confidence"], rows))
    proj = inputs.project()
    if proj and proj.get("components"):
        used = {i.get("existing_path") for i in items(inputs)}
        rows = [[f"<strong>{e(c.get('name'))}</strong>", f"<code>{e(c.get('path'))}</code>",
                 badge("used", "reuse") if c.get("path") in used else badge("not used")]
                for c in list_of(proj.get("components"))]
        parts.append("<h3>Existing components found</h3>" + table(["Component", "File", "In this design"], rows))
    return "".join(parts) or '<p class="empty">The plan has no items.</p>'


def _node_id(prefix, name):
    return prefix + "_" + (re.sub(r"[^A-Za-z0-9_]", "_", str(name)) or "x")


def _label(text):
    return re.sub(r'["#;<>]', "", str(text))


def graph_model(inputs):
    """Screens, components and tokens from the plan. A component used on several screens is one
    node holding every decision made for it. Edges are screen -> component only: the plan does
    not say which component uses which token, so none are drawn."""
    its = items(inputs)
    screens = {}
    for i in its:
        ref = str(i.get("design_ref", ""))
        screen = ref.split("/", 1)[0] if "/" in ref else None
        if i.get("level") == "screen" and screen:
            screens[screen] = str(i.get("name") or screen)
    comps, edges = {}, []
    for i in its:
        if i.get("level") in ("screen", "token"):
            continue
        name = str(i.get("name"))
        decisions = comps.setdefault(name, [])
        d = str(i.get("decision"))
        if d not in decisions:
            decisions.append(d)
        ref = str(i.get("design_ref", ""))
        screen = ref.split("/", 1)[0] if "/" in ref else None
        if screen in screens and (screen, name) not in edges:
            edges.append((screen, name))
    tokens = []
    for i in its:
        if i.get("level") == "token" and str(i.get("name")) not in tokens:
            tokens.append(str(i.get("name")))
    return screens, {n: f"{n} ({', '.join(d)})" for n, d in comps.items()}, edges, tokens


def derived_graph(inputs) -> str:
    screens, comps, edges, tokens = graph_model(inputs)
    lines = ["graph LR"]
    for screen, label in screens.items():
        lines.append(f'  {_node_id("s", screen)}["{_label(label)}"]')
    for name, label in comps.items():
        lines.append(f'  {_node_id("c", name)}["{_label(label)}"]')
    for screen, name in edges:
        lines.append(f'  {_node_id("s", screen)} --> {_node_id("c", name)}')
    if tokens:
        lines.append('  subgraph Tokens')
        for t in tokens:
            lines.append(f'    {_node_id("t", t)}(["{_label(t)}"])')
        lines.append("  end")
    return "\n".join(lines)


def graph_svg(inputs):
    """The component graph as inline SVG (no script), or None when the plan has no items."""
    screens, comps, edges, tokens = graph_model(inputs)
    if not (screens or comps or tokens):
        return None
    row, box_h, col_w = 46, 32, 230
    xs = {"s": 16, "c": 16 + col_w + 90, "t": 16 + 2 * (col_w + 90)}
    pos = {}
    out = []

    def column(kind, labels):
        for n, (key, label) in enumerate(labels):
            pos[(kind, key)] = (xs[kind], 40 + n * row)

    column("s", list(screens.items()))
    column("c", list(comps.items()))
    column("t", [(t, t) for t in tokens])
    rows = max(len(screens), len(comps), len(tokens), 1)
    height, width = 40 + rows * row, xs["t"] + col_w + 16
    for screen, name in edges:
        x1, y1 = pos[("s", screen)]
        x2, y2 = pos[("c", name)]
        out.append(f'<line x1="{x1 + col_w}" y1="{y1 + box_h // 2}" x2="{x2}" y2="{y2 + box_h // 2}" '
                   f'stroke="var(--muted)" stroke-width="1.5"/>')
    heads = {"s": "Screens", "c": "Components", "t": "Tokens"}
    for kind, present in (("s", screens), ("c", comps), ("t", tokens)):
        if present:
            out.append(f'<text x="{xs[kind]}" y="22" fill="var(--muted)" font-size="12" font-weight="600">{heads[kind]}</text>')
    labelled = [("s", screens.items()), ("c", comps.items()), ("t", [(t, t) for t in tokens])]
    for kind, pairs in labelled:
        for key, label in pairs:
            x, y = pos[(kind, key)]
            fill = {"s": "var(--accent-soft)", "c": "var(--card)", "t": "var(--bg)"}[kind]
            out.append(f'<rect x="{x}" y="{y}" width="{col_w}" height="{box_h}" rx="8" fill="{fill}" stroke="var(--line)"/>'
                       f'<text x="{x + 10}" y="{y + box_h // 2 + 4}" fill="var(--ink)" font-size="13">{e(label)}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
            f'style="max-width:100%;height:auto" role="img" aria-label="Component graph: screens, components and tokens">'
            + "".join(out) + "</svg>")


def section_graph(inputs, allow_cdn=False) -> str:
    source = None
    if inputs.plan_md:
        m = re.search(r"```mermaid\s*\n(.*?)```", inputs.plan_md, re.S)
        if m and m.group(1).strip():
            source = m.group(1).strip()
    svg = graph_svg(inputs)
    if source is None:
        if svg is None:
            return not_run("plan.json", "plan")
        source = derived_graph(inputs)
    src = e(source)
    # The plan's own mermaid diagram is only drawn with --allow-cdn; otherwise the derived SVG
    # (when the plan has items) and the source as text.
    if allow_cdn:
        shown = f'<div class="graph"><pre class="mermaid">{src}</pre></div>'
        note = "Graph source"
    elif svg is not None:
        shown = f'<div class="graph">{svg}</div>'
        note = "Graph source (mermaid syntax)"
    else:
        shown = ""
        note = "Graph source (mermaid syntax; run with --allow-cdn to draw it)"
    open_attr = "" if shown else " open"
    return f"{shown}<details{open_attr}><summary>{note}</summary><pre>{src}</pre></details>"


def _untranslated(inputs):
    """{locale: count} from todos.json 'translate N new strings' entries."""
    out = {}
    for t in list_of(inputs.todos):
        m = re.search(r"translate (\d+)", str(t.get("text", "")))
        loc = re.search(r"_([A-Za-z]{2,3}(?:[_-][A-Za-z0-9]+)?)\.(arb|json|xml|strings|xcstrings)$", str(t.get("file", "")))
        if m and loc:
            out[loc.group(1)] = out.get(loc.group(1), 0) + int(m.group(1))
    return out


def section_localization(inputs) -> str:
    proj = inputs.project()
    if proj is None and inputs.plan is None:
        return not_run("project-profile.json and plan.json", "scan-project")
    parts = []
    strs = strings(inputs)
    added = sum(1 for s in strs if not s.get("existing"))
    reused = sum(1 for s in strs if s.get("existing"))
    loc = as_dict((proj or {}).get("localization"))
    locales = string_list(loc.get("locales"))
    untranslated = _untranslated(inputs)
    rtl_issues = [(r.get("id"), x) for r in results(inputs) for x in string_list(r.get("rtl_issues"))]
    assets = list_of((inputs.manifest or {}).get("assets"))
    landed = asset_landings(inputs)
    cards = [card(added, "keys added", accent=True), card(reused, "keys reused"),
             card(len(locales) or "–", "locales"), card(sum(untranslated.values()), "strings to translate"),
             card(len(rtl_issues) if inputs.verify is not None else "–", "RTL issues"),
             card(len(landed) if inputs.state is not None else "–", "assets created"),
             card(len(assets), "design assets")]
    parts.append('<div class="cards">' + "".join(cards) + "</div>")
    if proj:
        rtl = loc.get("rtl") or any(l.split("_")[0].split("-")[0] in RTL_LOCALES for l in locales)
        parts.append(f"<p><strong>System:</strong> {e(loc.get('system', 'none'))}"
                     f"{' · files in <code>' + e(loc.get('location')) + '</code>' if loc.get('location') else ''}"
                     f" · right-to-left: {'yes' if rtl else 'no'}</p>")
    if locales:
        rows = [[f"<code>{e(l)}</code>", e(added), e(reused),
                 badge(f"{untranslated[l]} to translate", "medium") if untranslated.get(l) else badge("complete", "pass")]
                for l in locales]
        parts.append(table(["Locale", "Keys added", "Keys reused", "Status"], rows))
    if strs:
        rows = [[f"<code>{e(s.get('key'))}</code>", e(s.get("value")), e(s.get("screen")),
                 badge("reused", "reuse") if s.get("existing") else badge("added", "new")] for s in strs]
        parts.append("<h3>Strings</h3>" + table(["Key", "Text", "Screen", ""], rows))
    parts.append("<h3>Right-to-left</h3>")
    if inputs.verify is None:
        parts.append(not_run("verify/summary.json", "verify"))
    elif rtl_issues:
        parts.append('<ul>' + "".join(f"<li><code>{e(i)}</code>: {e(x)}</li>" for i, x in rtl_issues) + "</ul>")
    else:
        parts.append('<p class="muted">No RTL issues found in the rendered states.</p>')
    parts.append(direction_gallery(inputs))
    if assets:
        rows = [[e(a.get("name")), badge(a.get("kind")), f"<code>{e(a.get('path'))}</code>",
                 f"<code>{e(landed[a.get('name')])}</code>" if a.get("name") in landed else badge("not in project", "keep")]
                for a in assets]
        parts.append("<h3>Assets</h3>" + table(["Asset", "Kind", "Extracted from design", "Created in project"], rows))
    return "".join(parts)


def direction_gallery(inputs) -> str:
    """Per rendered state that has an RTL or pseudo-locale capture: LTR, RTL and pseudo side by side."""
    if not isinstance(inputs.verify, dict):
        return ""
    shots, pseudo_issues = [], []
    for r in results(inputs):
        rid = str(r.get("id", ""))
        if not re.fullmatch(r"[A-Za-z0-9_-]+(?:@[0-9]+--[A-Za-z0-9_-]+)?", rid) or not r.get("rendered"):
            continue
        folder = inputs.dir / "verify" / rid
        rtl, pseudo = folder / "rtl.png", folder / "pseudo.png"
        if not (rtl.is_file() or pseudo.is_file()):
            continue
        ltr = folder / f"iter-{r.get('iterations') or 1}" / "rendered.png"
        figs = figure(ltr, "Left-to-right") + (figure(rtl, "Right-to-left") if rtl.is_file() else "")
        figs += figure(pseudo, "Pseudo-locale") if pseudo.is_file() else ""
        shots.append(f'<article class="shot"><header><strong>{e(rid)}</strong></header>'
                     f'<div class="triptych">{figs}</div></article>')
        pseudo_issues += [(rid, x) for x in string_list(r.get("pseudo_issues"))]
    if not shots:
        return ""
    html = '<div class="shots">' + "".join(shots) + "</div>"
    if pseudo_issues:
        html += ("<h3>Pseudo-locale</h3><ul>"
                 + "".join(f"<li><code>{e(i)}</code>: {e(x)}</li>" for i, x in pseudo_issues) + "</ul>")
    return html


def _measured(m):
    if not isinstance(m, dict):
        return ""
    bits = []
    swatches = [v for v in m.values() if is_hex(v)]
    if swatches:
        bits.append('<span class="pair">' + "".join(chip(h) for h in swatches) + "</span>")
    for k, v in m.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            bits.append(f"<code>{e(k)}: {e(v)}</code>")
    return " ".join(bits)


def section_audit(inputs) -> str:
    parts = []
    if isinstance(inputs.manifest, dict):
        colors = list_of((inputs.manifest.get("tokens") or {}).get("colors"))
        if colors:
            sw = "".join(f'<div class="swatch">{chip(c.get("hex"))}<div><strong>{e(c.get("hex"))}</strong>'
                         f'<div class="muted">{e(c.get("name") or "unnamed")}</div></div></div>' for c in colors)
            parts.append(f'<h3>Palette</h3><div class="swatches">{sw}</div>')
    parts.append("<h3>Measured findings</h3>")
    if not isinstance(inputs.audit, dict):
        parts.append(not_run("design-audit.json", "plan"))
    else:
        findings = sorted(list_of(inputs.audit.get("findings")),
                          key=lambda f: SEVERITY_ORDER.get(f.get("severity"), 9))
        if findings:
            rows = []
            for f in findings:
                where = f.get("screen", "")
                if f.get("state"):
                    where += f"/{f['state']}"
                also = f.get("also_in") or []
                if also:
                    where += f" (+{len(also)} more)"
                rows.append([badge(f.get("severity"), f.get("severity")), e(f.get("category")), e(where),
                             f"{e(f.get('detail'))}<br>{_measured(f.get('measured'))}",
                             f'<span class="muted">{e(f.get("guideline"))}</span>'])
            parts.append(table(["Severity", "Category", "Where", "Finding", "Guideline"], rows))
        else:
            parts.append('<p class="muted">No measured issues.</p>')
    parts.append("<h3>Design suggestions</h3>")
    if not isinstance(inputs.plan, dict):
        parts.append(not_run("plan.json", "plan"))
    else:
        sugs = sorted(list_of(inputs.plan.get("design_suggestions")),
                      key=lambda s: SEVERITY_ORDER.get(s.get("severity"), 9))
        if sugs:
            rows = []
            for s in sugs:
                choice = s.get("choice", "keep")
                rows.append([f"<strong>{e(s.get('title'))}</strong><br><span class='muted'>{e(s.get('evidence'))}</span>",
                             f"{e(s.get('change'))}<br><span class='muted'>{e(s.get('why'))}</span>",
                             e(s.get("guideline")), badge(s.get("severity"), s.get("severity")),
                             badge(choice, "apply" if choice == "apply" else "keep")])
            parts.append(table(["Suggestion", "Change", "Guideline", "Severity", "Decision"], rows))
        else:
            parts.append('<p class="muted">No design suggestions.</p>')
    devs = list_of(inputs.deviations)
    if devs:
        rows = [[f"<code>{e(d.get('suggestion_id'))}</code>", e(f"{d.get('screen')}/{d.get('state')}"),
                 e(d.get("region")), e(d.get("note"))] for d in devs]
        parts.append("<h3>Intentional deviations from the design</h3>" + table(["Suggestion", "State", "Region", "What was built"], rows))
    return "".join(parts)


def section_files(inputs) -> str:
    if inputs.state is None:
        return not_run("state.json", "build")
    gen, chg = file_list(inputs, "generated_files"), file_list(inputs, "changed_files")
    if not gen and not chg:
        return '<p class="muted">No files recorded: Sauces has not written to the project yet.</p>'
    rows = [[f"<code>{e(f)}</code>", badge("new", "new")] for f in gen]
    rows += [[f"<code>{e(f)}</code>", badge("changed", "extend")] for f in chg]
    return (f'<p class="muted">{len(gen)} created, {len(chg)} changed. Generated code carries no markers, '
            "so use this list to review or revert Sauces' work.</p>" + table(["File", ""], rows))


def section_todos(inputs) -> str:
    if inputs.todos is None:
        return not_run("todos.json", "build")
    todos = list_of(inputs.todos)
    if not todos:
        return '<p class="muted">No TODOs: nothing needs a human.</p>'
    rows = [[f"<code>{e(t.get('file'))}:{e(t.get('line'))}</code>", e(t.get("text"))] for t in todos]
    return table(["Where", "What"], rows)


def _sample(findings, n=3):
    return ", ".join(f"{f.get('file')}:{f.get('line')}" for f in findings[:n]) + (" …" if len(findings) > n else "")


def practice_checks(inputs, platform):
    """[(text, state, evidence)] with state 'pass', 'warn' or 'unchecked'. A practice is ticked
    only when a result file shows it; with no evidence it is 'not checked'."""
    rendered = [r for r in results(inputs) if r.get("rendered")]
    rtl = sum(len(string_list(r.get("rtl_issues"))) for r in results(inputs))
    lint = inputs.lint.get("findings") if isinstance(inputs.lint, dict) and isinstance(inputs.lint.get("findings"), list) else None
    lint = [f for f in lint if isinstance(f, dict)] if lint is not None else None
    sugs = [s for s in list_of((inputs.plan or {}).get("design_suggestions")) if s.get("category") == "accessibility"]
    code_todos = [t for t in list_of(inputs.todos) if not re.search(r"translate \d+", str(t.get("text", "")))]
    none = ("unchecked", "no evidence in .sauces/")

    def lint_check(rule, label):
        if lint is None:
            return ("unchecked", "no lint results (.sauces/lint.json)")
        bad = [f for f in lint if f.get("rule") == rule]
        return ("warn", f"{len(bad)} {label} in {_sample(bad)}") if bad else ("pass", f"lint: no {label}")

    def evidence(key):
        if key == "tokens":
            return lint_check("hardcoded-color", "color literal(s)")
        if key == "strings":
            return lint_check("hardcoded-string", "hardcoded string(s)")
        if key == "rtl":
            if rtl:
                return ("warn", f"{rtl} RTL issue(s), see Localization")
            if rendered:
                return ("pass", f"no RTL issues in {len(rendered)} rendered state(s)")
            return ("unchecked", "verify has not rendered any state")
        if key == "states":
            res = results(inputs)
            if not res:
                return ("unchecked", "verify has not run")
            if len(rendered) == len(res):
                return ("pass", f"{len(rendered)} of {len(res)} states rendered from seeded state")
            return ("warn", f"{len(res) - len(rendered)} of {len(res)} states could not be rendered")
        if key == "a11y":
            kept = [s for s in sugs if s.get("choice") != "apply"]
            if kept:
                return ("warn", "kept without applying: " + ", ".join(str(s.get("title")) for s in kept))
            if sugs:
                return ("pass", "applied: " + ", ".join(str(s.get("title")) for s in sugs))
            return none
        if key == "todos":
            if code_todos:
                return ("pass", f"{len(code_todos)} TODO(sauces) marker(s) recorded in todos.json")
            return none
        return ("unchecked", "needs a code review; the report cannot verify it")

    return [(text, *evidence(key)) for key, text in PRACTICES.get(platform, GENERIC_PRACTICES)]


def section_practices(inputs) -> str:
    platform = inputs.platform()
    if platform is None:
        return not_run("project-profile.json", "scan-project")
    marks = {"pass": ("✓ followed", "pass"), "warn": ("⚠ check", "medium"), "unchecked": ("not checked", "keep")}
    lis = []
    for text, state, why in practice_checks(inputs, platform):
        label, kind = marks[state]
        lis.append(f"<li>{badge(label, kind)} {e(text)} <span class=\"muted\">{e(why)}</span></li>")
    applied = '<ul class="clean">' + "".join(lis) + "</ul>"
    steps = []
    todos = list_of(inputs.todos)
    code_todos = [t for t in todos if not re.search(r"translate \d+", str(t.get("text", "")))]
    if code_todos:
        steps.append(f"Resolve {len(code_todos)} TODO(sauces) item(s), starting with <code>{e(code_todos[0].get('file'))}</code>.")
    for loc, n in sorted(_untranslated(inputs).items()):
        steps.append(f"Translate {e(n)} new string(s) for <code>{e(loc)}</code>.")
    failed = [r for r in results(inputs) if r.get("rendered") and not r.get("passed")]
    if failed:
        steps.append("Review the states below the fidelity threshold: " + ", ".join(f"<code>{e(r.get('id'))}</code>" for r in failed) + ".")
    unrendered = [r for r in results(inputs) if not r.get("rendered")]
    if unrendered:
        steps.append("Check the unrendered states by hand with <code>.sauces/verify/checklist.md</code>.")
    rtl = sum(len(string_list(r.get("rtl_issues"))) for r in results(inputs))
    if rtl:
        steps.append(f"Fix {rtl} right-to-left issue(s) listed under Localization.")
    if isinstance(inputs.manifest, dict) and any(s.get("status") == "unreadable" for s in list_of(inputs.manifest.get("sources"))):
        steps.append("Make the unreadable sources available (for example connect the Figma MCP) and run <code>/sauces:cook</code> again.")
    kept = [s for s in list_of((inputs.plan or {}).get("design_suggestions")) if s.get("choice") != "apply"
            and s.get("severity") == "high"] if isinstance(inputs.plan, dict) else []
    if kept:
        steps.append(f"Reconsider {len(kept)} high-severity design suggestion(s) you kept.")
    if inputs.verify is None:
        steps.append("Run <code>/sauces:verify</code> to score the built screens against the design.")
    if not inputs.gitignores_verify():
        steps.append("Add <code>.sauces/verify/</code> to <code>.gitignore</code>.")
    next_html = "<ol>" + "".join(f"<li>{s}</li>" for s in steps) + "</ol>"
    return (f'<div class="cols"><div><h3>Practices checked against this run ({e(platform)})</h3>{applied}</div>'
            f"<div><h3>Next steps</h3>{next_html}</div></div>")


def section_recommendations(inputs) -> str:
    if not isinstance(inputs.plan, dict):
        return not_run("plan.json", "plan")
    parts = []
    recs = list_of(inputs.plan.get("recommendations"))
    if recs:
        rows = []
        for r in recs:
            options = {o.get("id"): o for o in list_of(r.get("options"))}
            choice = r.get("choice", "keep")
            opt = options.get(choice, {})
            files = "".join(f"<br><code>{e(f)}</code>" for f in opt.get("files") or [])
            rows.append([f"<strong>{e(r.get('title'))}</strong><br><span class='muted'>{e(r.get('why'))}</span>",
                         badge("kept as is", "keep") if choice == "keep" else badge("applied", "apply"),
                         f"{e(opt.get('label') or choice)}{files}"])
        parts.append(table(["Recommendation", "Decision", "Chosen option"], rows))
    else:
        parts.append('<p class="muted">No recommendations: the project already follows the practices Sauces checks.</p>')
    deps = list_of(inputs.plan.get("dependency_changes"))
    if deps:
        rows = [[f"<code>{e(d.get('package'))}</code>", e(d.get("version")), e(d.get("scope")), e(d.get("reason"))] for d in deps]
        parts.append("<h3>Dependency changes</h3>" + table(["Package", "Version", "Scope", "Why"], rows))
    return "".join(parts)


# ---------- page ----------

def heading(inputs):
    names = [s.get("name") or s.get("id") for s in list_of((inputs.manifest or {}).get("screens"))] \
        if isinstance(inputs.manifest, dict) else []
    title = ", ".join(str(n) for n in names[:4]) or "Design to code"
    if len(names) > 4:
        title += f" and {len(names) - 4} more"
    platform = inputs.platform()
    sub = []
    if platform:
        sub.append(f"Built for {platform}")
    if isinstance(inputs.plan, dict) and inputs.plan.get("approved"):
        sub.append(f"plan approved by {inputs.plan.get('approved_by') or 'user'}")
    return title, " · ".join(sub) or "Sauces pipeline results"


def mermaid_script() -> str:
    return (f'<script src="https://cdn.jsdelivr.net/npm/mermaid@{MERMAID_VERSION}/dist/mermaid.min.js" '
            f'integrity="{MERMAID_SRI}" crossorigin="anonymous"></script>\n'
            "<script>if (window.mermaid) { mermaid.initialize({ startOnLoad: true, theme: "
            "matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'default' }); }</script>")


def render(inputs, template: str, allow_cdn: bool = False) -> str:
    title, sub = heading(inputs)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    values = {
        "title": e(f"Sauces report: {title}"),
        "heading": e(title),
        "subheading": e(sub),
        "summary": section_summary(inputs),
        "fidelity": section_fidelity(inputs),
        "design_system": section_design_system(inputs),
        "graph": section_graph(inputs, allow_cdn),
        "localization": section_localization(inputs),
        "audit": section_audit(inputs),
        "files": section_files(inputs),
        "todos": section_todos(inputs),
        "practices": section_practices(inputs),
        "recommendations": section_recommendations(inputs),
        "mermaid": mermaid_script() if allow_cdn else "",
        "footer": e(f"Generated by Sauces on {generated}. We make the sauce; you make the sandwich."),
    }
    # One pass over the template, so placeholder-like text inside the values stays as is.
    return re.sub(r"\{\{(\w+)\}\}", lambda m: values.get(m.group(1), m.group(0)), template)


def main(argv=None):
    args = parse_args(argv)
    sauces = Path(args.sauces_dir)
    if not sauces.is_dir():
        print(f"Not a folder: {sauces}", file=sys.stderr)
        return 2
    template_path = Path(args.template) if args.template else DEFAULT_TEMPLATE
    if not template_path.is_file():
        print(f"Template not found: {template_path}", file=sys.stderr)
        return 2
    require_deps()
    inputs = Inputs(sauces)
    html = render(inputs, template_path.read_text(encoding="utf-8"), args.allow_cdn)
    out = Path(args.output) if args.output else sauces / "report.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
