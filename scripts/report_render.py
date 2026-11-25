#!/usr/bin/env python3
"""Render the Sauces report.html from the pipeline's .sauces/ working state.

Fills skills/report/assets/report-template.html with the manifest, project
profile, plan, design audit, build outputs (todos, deviations, state) and
verify results. The page is self-contained: inline CSS, screenshots embedded
as data URIs; the only external resource is the mermaid CDN script, and the
graph source is also shown as plain text.

A missing or unreadable input makes its section say "not run". All text from
the inputs is HTML-escaped.

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

# What the generated code follows, per platform. Each line holds only when the matching
# build reference was followed; the summary's checks section says whether lint/tests ran.
PRACTICES = {
    "flutter": [
        "Colors and type come from the theme (ColorScheme, TextTheme, ThemeExtension), never Colors.* or hex literals.",
        "Every user-facing string lives in the localization files of every locale; non-source locales are marked for translation.",
        "Directional layout (EdgeInsetsDirectional, AlignmentDirectional) so right-to-left locales mirror correctly.",
        "Existing components are extended with optional parameters whose defaults keep today's behavior.",
        "Each screen state can be shown by seeding its state class, which is how tests and verify render it.",
        "Touch targets of at least 48 dp, semantics labels from l10n, and no fixed-height text containers.",
        "Unknown behavior (API calls, navigation) is a TODO(sauces) comment, never a fake.",
    ],
}
GENERIC_PRACTICES = [
    "Design values come from the project's tokens and theme, not literals.",
    "User-facing strings live in the project's string resources.",
    "Existing components are extended, never silently replaced.",
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
        self.manifest = self._load("manifest.json")
        self.profile = self._load("project-profile.json")
        self.plan = self._load("plan.json")
        self.audit = self._load("design-audit.json")
        self.state = self._load("state.json")
        self.todos = self._load("todos.json")
        self.deviations = self._load("deviations.json")
        self.verify = self._load("verify/summary.json")
        plan_md = sauces / "plan.md"
        self.plan_md = plan_md.read_text(encoding="utf-8", errors="replace") if plan_md.is_file() else None

    def _load(self, name):
        path = self.dir / name
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            self.problems.append(f"{name}: {exc}")
            return None

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
        projects = self.profile.get("projects") or []
        platform = (self.plan or {}).get("platform")
        for proj in projects:
            if proj.get("platform") == platform:
                return proj
        return projects[0] if projects else None

    def platform(self):
        if isinstance(self.plan, dict) and self.plan.get("platform"):
            return self.plan["platform"]
        proj = self.project()
        return proj.get("platform") if proj else None


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


# ---------- sections ----------

def section_summary(inputs) -> str:
    if inputs.manifest is None and inputs.plan is None:
        return not_run("manifest.json and plan.json", "cook")
    parts = []
    its = items(inputs)
    counts = {d: sum(1 for i in its if i.get("decision") == d and i.get("level") != "screen") for d in DECISIONS}
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
        loc = proj.get("localization") or {}
        facts = [
            ("Platform", proj.get("platform")),
            ("Architecture", proj.get("architecture")),
            ("State management", proj.get("state_management")),
            ("Localization", f"{loc.get('system', '?')} · {', '.join(loc.get('locales') or []) or 'no locales'}"),
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
        safe_id = rid if re.fullmatch(r"[A-Za-z0-9_-]+", rid) else None
        devs = r.get("deviations") or []
        if r.get("rendered") and safe_id:
            n = r.get("iterations") or 1
            it = inputs.dir / "verify" / safe_id / f"iter-{n}"
            ref = inputs.resolve(r.get("reference"))
            images = ('<div class="triptych">' + figure(ref, "design") + figure(it / "rendered.png", "built")
                      + figure(it / "diff.png", "difference") + "</div>")
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
        notes += [e(x) for x in r.get("remaining") or []]
        notes += [f"RTL: {e(x)}" for x in r.get("rtl_issues") or []]
        note_html = "<ul>" + "".join(f"<li>{n}</li>" for n in notes) + "</ul>" if notes else ""
        shots.append(f'<article class="shot"><header><strong>{e(rid)}</strong>{score}</header>{meta}{images}{note_html}</article>')
    if not shots:
        return '<p class="empty">No screen states were verified.</p>'
    renderer = inputs.verify.get("renderer")
    lead = f'<p class="muted">Rendered with {e(renderer)}.</p>' if renderer else ""
    return lead + '<div class="shots">' + "".join(shots) + "</div>"


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


def derived_graph(inputs) -> str:
    its = items(inputs)
    lines = ["graph LR"]
    screens = {}
    for i in its:
        ref = str(i.get("design_ref", ""))
        screen = ref.split("/", 1)[0] if "/" in ref else None
        if i.get("level") == "screen" and screen:
            screens[screen] = i
    for screen, i in screens.items():
        lines.append(f'  {_node_id("s", screen)}["{_label(i.get("name") or screen)}"]')
    seen = set()
    for i in its:
        ref = str(i.get("design_ref", ""))
        if i.get("level") in ("screen", "token"):
            continue
        cid = _node_id("c", i.get("name"))
        if cid not in seen:
            lines.append(f'  {cid}["{_label(i.get("name"))} ({_label(i.get("decision"))})"]')
            seen.add(cid)
        screen = ref.split("/", 1)[0] if "/" in ref else None
        if screen in screens:
            edge = f'  {_node_id("s", screen)} --> {cid}'
            if edge not in lines:
                lines.append(edge)
    tokens = [i for i in its if i.get("level") == "token"]
    for t in tokens:
        tid = _node_id("t", t.get("name"))
        lines.append(f'  {tid}(["{_label(t.get("name"))}"])')
        for cid in sorted(seen):
            lines.append(f"  {cid} -.-> {tid}")
    return "\n".join(lines)


def section_graph(inputs) -> str:
    source = None
    if inputs.plan_md:
        m = re.search(r"```mermaid\s*\n(.*?)```", inputs.plan_md, re.S)
        if m and m.group(1).strip():
            source = m.group(1).strip()
    if source is None:
        if not items(inputs):
            return not_run("plan.json", "plan")
        source = derived_graph(inputs)
    src = e(source)
    return (f'<div class="graph"><pre class="mermaid">{src}</pre></div>'
            f"<details><summary>Graph source (shown as text when the mermaid script can't load)</summary>"
            f"<pre>{src}</pre></details>")


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
    loc = (proj or {}).get("localization") or {}
    locales = loc.get("locales") or []
    untranslated = _untranslated(inputs)
    rtl_issues = [(r.get("id"), x) for r in results(inputs) for x in r.get("rtl_issues") or []]
    assets = list_of((inputs.manifest or {}).get("assets")) if isinstance(inputs.manifest, dict) else []
    cards = [card(added, "keys added", accent=True), card(reused, "keys reused"),
             card(len(locales) or "–", "locales"), card(sum(untranslated.values()), "strings to translate"),
             card(len(rtl_issues) if inputs.verify is not None else "–", "RTL issues"), card(len(assets), "assets")]
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
    if assets:
        rows = [[e(a.get("name")), badge(a.get("kind")), f"<code>{e(a.get('path'))}</code>"] for a in assets]
        parts.append("<h3>Assets</h3>" + table(["Asset", "Kind", "Source"], rows))
    return "".join(parts)


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


def section_todos(inputs) -> str:
    if inputs.todos is None:
        return not_run("todos.json", "build")
    todos = list_of(inputs.todos)
    if not todos:
        return '<p class="muted">No TODOs: nothing needs a human.</p>'
    rows = [[f"<code>{e(t.get('file'))}:{e(t.get('line'))}</code>", e(t.get("text"))] for t in todos]
    return table(["Where", "What"], rows)


def section_practices(inputs) -> str:
    platform = inputs.platform()
    if platform is None:
        return not_run("project-profile.json", "scan-project")
    practices = PRACTICES.get(platform, GENERIC_PRACTICES)
    applied = '<ul class="clean">' + "".join(f"<li>✓ {e(p)}</li>" for p in practices) + "</ul>"
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
    rtl = sum(len(r.get("rtl_issues") or []) for r in results(inputs))
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
    steps.append("Add <code>.sauces/verify/</code> to <code>.gitignore</code> if it isn't there.")
    next_html = "<ol>" + "".join(f"<li>{s}</li>" for s in steps) + "</ol>"
    return (f'<div class="cols"><div><h3>Followed in the generated code ({e(platform)})</h3>{applied}</div>'
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


def render(inputs, template: str) -> str:
    title, sub = heading(inputs)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    values = {
        "title": e(f"Sauces report: {title}"),
        "heading": e(title),
        "subheading": e(sub),
        "summary": section_summary(inputs),
        "fidelity": section_fidelity(inputs),
        "design_system": section_design_system(inputs),
        "graph": section_graph(inputs),
        "localization": section_localization(inputs),
        "audit": section_audit(inputs),
        "todos": section_todos(inputs),
        "practices": section_practices(inputs),
        "recommendations": section_recommendations(inputs),
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
    html = render(inputs, template_path.read_text(encoding="utf-8"))
    out = Path(args.output) if args.output else sauces / "report.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
