#!/usr/bin/env python3
"""Lint generated UI code for hard-coded colors and user-facing strings (Sauces).

Stdlib only. Usage: lint_generated.py --platform PLATFORM [--allow GLOB ...]
[--allow-colors GLOB ...] files...

Prints {"version":1,"findings":[{"file","line","rule","text"}]} on stdout.
Exit codes: 0 clean, 1 findings, 2 usage error (unknown platform, missing file).

Comments are blanked (line numbers preserved) before matching, so commented-out
code never flags. A `// sauces-lint-ignore` comment on a line suppresses findings
that start on that line. Files matching an allow glob are skipped; --allow globs
are added to the platform defaults. Files matching an --allow-colors glob (the project's
token files) skip only hardcoded-color; every other rule still applies to them.

hardcoded-string covers the first argument of Text()/SelectableText() and the value
of hintText:, labelText:, helperText:, errorText:, tooltip:, semanticsLabel:. In that
argument expression a non-empty string literal is a finding when it starts the argument
or directly follows `?`, `:` or `??` at the top level (ternary / null-coalescing forms).
Empty literals are allowed in every quote form. A literal whose whole body is exactly one
interpolation (`'$name'`, `'${l10n.count}'`) has no literal text and is allowed; any text
around the interpolation (`'Hi $name'`) is a finding. Raw strings never interpolate.

Web platforms (web-react) use a JS/TS/JSX scanner and a CSS declaration scanner:
- hardcoded-color: hex (#rgb, #rgba, #rrggbb, #rrggbbaa) and rgb/rgba/hsl/hsla/hwb/lab/lch/
  oklab/oklch() in CSS declaration values (never selectors; url(...) is ignored), in
  styled/template literals, Tailwind arbitrary values (bg-[#fff]) and string literals whose
  whole value is a color (except after href=, to=, id=, htmlFor=, key=). Named colors
  (`red`) are not flagged: too noisy.
- hardcoded-string: JSX text with a letter between an opening tag (<Name ...> or <>) and the
  next tag, ignoring {expressions}; and non-empty alt, title, placeholder, aria-label,
  aria-description, aria-placeholder attribute strings. Text after a closing tag is not checked.
- physical-direction: CSS margin/padding/border-left/right, left/right, text-align/float/clear
  left|right; style-object keys (marginLeft, paddingRight, borderLeft...); Tailwind physical
  utilities (ml- mr- pl- pr- left- right- border-l border-r rounded-l rounded-r text-left
  text-right float-left float-right, with variant prefixes) inside string/template literals.
- a11y-basic: <img> without alt; onClick on div/span; input/select/textarea with no
  aria-label, aria-labelledby, id referenced by an htmlFor in the same file (the same
  literal, or the same simple expression: htmlFor={id} / id={id}), <label> on the
  same or previous line, or type hidden/submit/button. Label matching is file-local.
CSS/SCSS files get only hardcoded-color and physical-direction.

web-html adds an html.parser-based markup linter (.html .htm .njk .liquid .astro, and HTML in
JS template literals that contain `<`):
- hardcoded-string: a text node with a letter needs data-i18n on itself or an ancestor; an
  alt/title/placeholder/aria-label value with a letter must be listed in the element's
  data-i18n-attr ("attr:key;attr2:key2"). Text made only of {{ }}, {% %}, { } or ${ }
  expressions, entities, digits or punctuation is allowed. <script>/<style> are skipped;
  an Astro --- frontmatter block at the top is skipped.
- inline-style: any style="" attribute.
- a11y-basic: <img> without alt; onclick on div/span; input/select/textarea with no
  <label for> matching its id, no enclosing <label>, no aria-label/aria-labelledby, unless
  type is hidden/submit/button/reset.
- html-parse: a non-void element left unclosed when an ancestor closes, reported at its
  opening line. Optional-close elements (p li dt dd tr td th thead tbody tfoot option
  optgroup colgroup caption rp rt) are exempt, and so is anything open at the end while
  html/body/head close implicitly. Not checked inside JS template literals (fragments).
In .js/.mjs files web-html checks literal colors, style-object/Tailwind physical direction
and the HTML inside template literals; there is no JSX text check.
<!-- sauces-lint-ignore --> or // sauces-lint-ignore on a line suppresses that line.
"""
import argparse
import html.parser
import json
import re
import sys
from pathlib import Path

IGNORE_MARKER = "sauces-lint-ignore"
MAX_TEXT = 200

_STRING_ARGS = r"(?:hintText|labelText|helperText|errorText|tooltip|semanticsLabel)"

COMPOSE_RULES = [
    ("hardcoded-color", re.compile(r"\bColor\s*\(\s*0[xX][0-9A-Fa-f]+")),
    ("hardcoded-string", re.compile(
        r"(?:\bText\(\s*(?:text\s*=\s*)?|\bcontentDescription\s*=\s*)(?P<arg>)")),
]

# RULES[platform] -> [(rule_id, regex)]. A regex with an empty named group `arg` marks the
# start of an argument expression whose string literals are checked (see docstring).
RULES = {
    "flutter": [
        ("hardcoded-color", re.compile(
            r"Color\(0x|Color\.fromARGB|Color\.fromRGBO|\bColors\.(?!transparent\b)")),
        ("hardcoded-string", re.compile(
            r"(?:\b(?:Text|SelectableText)\(\s*|\b" + _STRING_ARGS + r":\s*)"
            r"(?P<arg>)")),
    ],
    "android-compose": COMPOSE_RULES,
    "kmp-cmp": COMPOSE_RULES,
    "react-native": [
        ("hardcoded-color", re.compile(
            r"\b(?:color|[a-zA-Z]+Color)\s*:\s*[\"']"
            r"(?:#(?:[a-fA-F0-9]{8}|[a-fA-F0-9]{6}|[a-fA-F0-9]{4}|[a-fA-F0-9]{3})[\"']"
            r"|(?:rgba?|hsla?)\()")),
        ("hardcoded-string", re.compile(
            r"<Text(?:\s+[^<>]*?)?>\s*(?=[^\s<{])[^<{}]*\w[^<{}]*</Text\s*>"
            r"|\b(?:accessibilityLabel|accessibilityHint|placeholder)\s*=\s*"
            r"[\"'][^\"'\n]+[\"']")),
    ],
    "ios-swiftui": [
        ("hardcoded-color", re.compile(r"\bColor\s*\(\s*(?:red|white)\s*:")),
        # SwiftUI localizes Text("Key") through LocalizedStringKey.
        ("hardcoded-string", re.compile(r"\bText\(\s*verbatim\s*:\s*(?P<arg>)")),
    ],
}
EXTENSIONS = {
    "flutter": (".dart",),
    "android-compose": (".kt",),
    "ios-swiftui": (".swift",),
    "kmp-cmp": (".kt",),
    "react-native": (".js", ".jsx", ".ts", ".tsx"),
    "web-react": (".js", ".jsx", ".ts", ".tsx", ".css", ".scss"),
    "web-html": (".html", ".htm", ".css", ".js", ".mjs", ".njk", ".liquid", ".astro"),
}
DEFAULT_ALLOW = {
    "flutter": ["**/theme/**", "**/*_strings.dart", "**/l10n/**", "**/*.g.dart"],
}


def glob_to_regex(glob):
    """Translate a glob to a regex; `**/` also matches zero directories."""
    i, out = 0, []
    while i < len(glob):
        c = glob[i]
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("".join(out))


def is_allowed(path, globs):
    forms = {str(path), Path(path).as_posix(), str(path).replace("\\", "/")}
    return any(g.fullmatch(f) for g in globs for f in forms)


def scan(src):
    """Return (masked, literals). masked has comments replaced by spaces (newlines kept).
    literals maps the start offset of each string literal to its end offset."""
    n = len(src)
    out = list(src)
    literals = {}

    def blank(a, b):
        for k in range(a, b):
            if out[k] != "\n":
                out[k] = " "

    def string(i):
        start = i
        if src[i] == "r":
            raw = True
            i += 1
        else:
            raw = False
        q = src[i]
        triple = src.startswith(q * 3, i)
        i += 3 if triple else 1
        while i < n:
            c = src[i]
            if c == "\\" and not raw:
                i += 2
                continue
            if triple and src.startswith(q * 3, i):
                i += 3
                break
            if not triple and c == q:
                i += 1
                break
            if not triple and c == "\n":
                break  # unterminated; recover at end of line
            if c == "$" and not raw and i + 1 < n and src[i + 1] == "{":
                i = code(i + 2, True)
                continue
            i += 1
        literals[start] = i
        return i

    def code(i, in_interp):
        depth = 0
        while i < n:
            c = src[i]
            if src.startswith("//", i):
                j = src.find("\n", i)
                j = n if j < 0 else j
                blank(i, j)
                i = j
            elif src.startswith("/*", i):
                j, d = i + 2, 1  # Dart block comments nest
                while j < n and d:
                    if src.startswith("/*", j):
                        d += 1
                        j += 2
                    elif src.startswith("*/", j):
                        d -= 1
                        j += 2
                    else:
                        j += 1
                blank(i, j)
                i = j
            elif c in "'\"":
                i = string(i)
            elif c == "r" and i + 1 < n and src[i + 1] in "'\"" and not (
                    i > 0 and (src[i - 1].isalnum() or src[i - 1] in "_$")):
                i = string(i)
            elif in_interp and c == "{":
                depth += 1
                i += 1
            elif in_interp and c == "}":
                if depth == 0:
                    return i + 1
                depth -= 1
                i += 1
            else:
                i += 1
        return i

    code(0, False)
    return "".join(out), literals


def inside_literal(pos, literals):
    return any(a < pos < b for a, b in literals.items())


INTERPOLATION_ONLY = re.compile(r"\$[A-Za-z_]\w*|\$\{[^{}]*\}")
TERNARY_TAIL = re.compile(r"(?:\?\?|\?|:)\s*$")


def has_text(src, start, end):
    """True if the literal src[start:end] has user-facing literal text."""
    body = src[start:end]
    raw = body.startswith("r")
    if raw:
        body = body[1:]
    q = body[:1]
    inner = body[3:-3] if body.startswith(q * 3) and len(body) >= 6 else body[1:-1]
    if inner == "":
        return False
    return raw or not INTERPOLATION_ONLY.fullmatch(inner)


def arg_literals(masked, literals, pos):
    """Start offsets of string literals in the argument expression beginning at pos:
    the first token, plus any literal directly after ?, : or ?? at depth 0."""
    out, depth, i, n = [], 0, pos, len(masked)
    while i < n:
        if i in literals:
            if not masked[pos:i].strip() or (depth == 0 and TERNARY_TAIL.search(masked[pos:i])):
                out.append(i)
            i = literals[i]
            continue
        c = masked[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                break
            depth -= 1
        elif (c == "," or c == ";") and depth == 0:
            break
        i += 1
    return out


def lint_file(path, rules):
    src = Path(path).read_text(encoding="utf-8", errors="replace")
    masked, literals = scan(src)
    lines = src.split("\n")

    def line_of(pos):
        return masked.count("\n", 0, pos) + 1

    found = []
    for rule_id, rx in rules:
        for m in rx.finditer(masked):
            if inside_literal(m.start(), literals):
                continue
            hits = 1
            if "arg" in rx.groupindex:
                hits = sum(1 for st in arg_literals(masked, literals, m.end())
                           if has_text(src, st, literals[st]))
            ln = line_of(m.start())
            text = lines[ln - 1] if ln <= len(lines) else ""
            if IGNORE_MARKER in text:
                continue
            for _ in range(hits):
                found.append({"file": str(path), "line": ln, "rule": rule_id,
                              "text": text.strip()[:MAX_TEXT]})
    return found


# ------------------------------------------------------------------- web platforms

HEX = r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})(?![\w-])"
COLOR_FN = re.compile(r"(?<![\w-])(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\(", re.I)
COLOR_IN_VALUE = re.compile(HEX + r"|(?<![\w-])(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\(", re.I)
URL_FN = re.compile(r"url\([^)]*\)", re.I)
WHOLE_HEX = re.compile(r"\s*" + HEX + r"\s*")
BRACKET_HEX = re.compile(r"\[\s*" + HEX)
NON_COLOR_ATTR = re.compile(r"\b(?:href|to|id|htmlFor|key)\s*=\s*\{?\s*$")
CSS_PHYSICAL_PROP = re.compile(
    r"(?:margin|padding)-(?:left|right)|border-(?:left|right)(?:-[\w-]+)?"
    r"|border-(?:top|bottom)-(?:left|right)-radius|left|right", re.I)
CSS_PHYSICAL_VALUE = re.compile(r"(?:text-align|float|clear)", re.I)
DECL = re.compile(r"\s*(\$?[-\w]+)\s*:(.*)", re.S)
JS_PHYSICAL = re.compile(
    r"\b(?:margin|padding)(?:Left|Right)\b|\bborder(?:Top|Bottom)?(?:Left|Right)\w*"
    r"|\b(?:textAlign|float|clear)\s*:\s*[\"'`](?:left|right)[\"'`]")
TW_PHYSICAL = re.compile(
    r"(?<![\w/.\[-])(?:[\w-]+:)*-?(?:"
    r"(?:ml|mr|pl|pr|left|right|border-l|border-r|rounded-l|rounded-r)-[\w\[\]./%#-]+"
    r"|(?:text-left|text-right|float-left|float-right|border-l|border-r|rounded-l|rounded-r)"
    r"(?![\w-]))")
STRING_ATTRS = ("alt", "title", "placeholder", "aria-label", "aria-description",
                "aria-placeholder")
LETTER = re.compile(r"[^\W\d_]")
TAG_START = re.compile(r"<(?:([A-Za-z][\w.:-]*)|(>))")


def scan_js(src):
    """Return (masked, literals) for JS/TS: comments blanked; literals maps start -> end for
    '...', "..." and `...` (template interpolations are part of the literal)."""
    n, out, literals = len(src), list(src), {}

    def blank(a, b):
        for k in range(a, b):
            if out[k] != "\n":
                out[k] = " "

    def string(i):
        start, q = i, src[i]
        i += 1
        while i < n:
            c = src[i]
            if c == "\\":
                i += 2
                continue
            if c == q:
                i += 1
                break
            if q != "`" and c == "\n":
                break
            if q == "`" and src.startswith("${", i):
                i = code(i + 2, True)
                continue
            i += 1
        literals[start] = min(i, n)
        return i

    def code(i, in_interp):
        depth = 0
        while i < n:
            c = src[i]
            if src.startswith("//", i):
                j = src.find("\n", i)
                j = n if j < 0 else j
                blank(i, j)
                i = j
            elif src.startswith("/*", i):
                j = src.find("*/", i + 2)
                j = n if j < 0 else j + 2
                blank(i, j)
                i = j
            elif c in "'\"`":
                i = string(i)
            elif in_interp and c == "{":
                depth += 1
                i += 1
            elif in_interp and c == "}":
                if depth == 0:
                    return i + 1
                depth -= 1
                i += 1
            else:
                i += 1
        return i

    code(0, False)
    return "".join(out), literals


def mask_css(src, scss):
    """Blank /* */ comments (and // line comments in SCSS) keeping offsets."""
    out = list(src)
    for m in re.finditer(r"/\*.*?(?:\*/|\Z)", src, re.S):
        for k in range(m.start(), m.end()):
            if out[k] != "\n":
                out[k] = " "
    if scss:
        for m in re.finditer(r"(?:(?<=\s)|^)//[^\n]*", src, re.M):
            for k in range(m.start(), m.end()):
                out[k] = " "
    return "".join(out)


def css_declarations(text, base=0):
    """Yield (prop, prop_offset, value, value_offset) for `prop: value` segments ended by
    ; or } (selectors end with { and are never declarations)."""
    start = 0
    for i, c in enumerate(text):
        if c in "{};":
            if c != "{":
                m = DECL.match(text, start, i)
                if m and m.group(1):
                    yield (m.group(1), base + m.start(1), m.group(2), base + m.start(2))
            start = i + 1


def css_findings(text, base, skip_colors):
    """[(offset, rule)] for CSS text starting at offset base."""
    hits = []
    for prop, poff, value, voff in css_declarations(text, base):
        p = prop.lower()
        if CSS_PHYSICAL_PROP.fullmatch(p) or (
                CSS_PHYSICAL_VALUE.fullmatch(p)
                and re.fullmatch(r"\s*(?:left|right)\s*(?:!important\s*)?", value, re.I)):
            hits.append((poff, "physical-direction"))
        if not skip_colors:
            clean = URL_FN.sub(lambda m: " " * len(m.group()), value)
            for m in COLOR_IN_VALUE.finditer(clean):
                hits.append((voff + m.start(), "hardcoded-color"))
    return hits


def jsx_tag_end(masked, literals, i):
    """Offset just past the `>` closing the tag whose name ends at i, and whether it is
    self-closing. Skips {expressions} and literals. None if no end is found."""
    depth, n = 0, len(masked)
    while i < n:
        if i in literals:
            i = literals[i]
            continue
        c = masked[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif depth == 0 and c == ">":
            return i + 1, masked[i - 1] == "/"
        elif depth == 0 and c in "<;":
            return None
        i += 1
    return None


def jsx_attrs(src, literals, a, b):
    """{name: (value_text or None, offset)} for attributes in src[a:b]."""
    attrs, i = {}, a
    while i < b:
        m = re.compile(r"\s*([A-Za-z_][\w:.-]*)").match(src, i, b)
        if not m:
            i += 1
            continue
        name, i = m.group(1), m.end()
        m2 = re.compile(r"\s*=\s*").match(src, i, b)
        if not m2:
            attrs[name] = (None, m.start(1))
            continue
        i = m2.end()
        if i in literals:
            attrs[name] = (src[i:literals[i]], i)
            i = literals[i]
        elif i < b and src[i] == "{":
            depth, j = 0, i
            while j < b:
                if j in literals:
                    j = literals[j]
                    continue
                depth += {"{": 1, "}": -1}.get(src[j], 0)
                j += 1
                if depth == 0:
                    break
            attrs[name] = (src[i:j], i)
            i = j
        else:
            attrs[name] = ("", i)
    return attrs


def literal_value(text):
    """Inner text of a quoted attribute value, or of {"..."}; None for expressions."""
    if text is None:
        return None
    t = text.strip()
    if t.startswith("{") and t.endswith("}"):
        t = t[1:-1].strip()
    if len(t) >= 2 and t[0] == t[-1] and t[0] in "'\"`" and "${" not in t:
        return t[1:-1]
    return None


def jsx_text_has_letters(masked, a):
    """True if the JSX text run starting at a (up to the next `<`) has a letter outside
    {expressions}; an unclosed { hides the rest of the run."""
    depth, i, n = 0, a, len(masked)
    while i < n and masked[i] != "<":
        c = masked[i]
        if c == "{":
            depth += 1
        elif c == "}" and depth:
            depth -= 1
        elif depth == 0 and LETTER.match(c):
            return True
        i += 1
    return False


def js_literal_findings(src, masked, literals, skip_colors):
    """Colors, Tailwind physical utilities and CSS-in-template inside literals, plus
    style-object physical keys in code."""
    hits = []
    for a, b in literals.items():
        body_a, body_b = a + 1, max(a + 1, b - 1)
        body = src[body_a:body_b]
        if src[a] == "`":
            hits += css_findings(body, body_a, skip_colors)
            if not skip_colors:
                hits += [(body_a + m.start(), "hardcoded-color") for m in BRACKET_HEX.finditer(body)]
        elif not skip_colors:
            if WHOLE_HEX.fullmatch(body) and not NON_COLOR_ATTR.search(masked[max(0, a - 40):a]):
                hits.append((a, "hardcoded-color"))
            else:
                ms = list(BRACKET_HEX.finditer(body)) + list(COLOR_FN.finditer(body)) + list(
                    re.finditer(r":\s*" + HEX, body))
                hits += [(body_a + m.start(), "hardcoded-color") for m in ms]
        hits += [(body_a + m.start(), "physical-direction") for m in TW_PHYSICAL.finditer(body)]
    for m in JS_PHYSICAL.finditer(masked):
        if not inside_literal(m.start(), literals):
            hits.append((m.start(), "physical-direction"))
    return hits


def react_findings(src, skip_colors):
    masked, literals = scan_js(src)
    hits = js_literal_findings(src, masked, literals, skip_colors)

    def inside(pos):
        return inside_literal(pos, literals)

    # JSX
    html_for = set()
    for m in re.finditer(r"\bhtmlFor\s*=\s*\{?\s*[\"'`]([^\"'`]+)", src):
        html_for.add(m.group(1))
    for m in re.finditer(r"\bhtmlFor\s*=\s*\{\s*([\w.$]+)\s*\}", src):
        html_for.add("{" + m.group(1) + "}")
    lines = src.split("\n")
    for m in TAG_START.finditer(masked):
        if inside(m.start()):
            continue
        k = m.start() - 1
        while k >= 0 and masked[k] in " \t\r\n":
            k -= 1
        if k >= 0 and (masked[k].isalnum() or masked[k] in "_$)]"):
            continue  # a < b, generics, comparisons
        name = m.group(1) or ""
        if m.group(2):
            end, self_closing = m.end(), False
        else:
            res = jsx_tag_end(masked, literals, m.end())
            if not res:
                continue
            end, self_closing = res
        attrs = jsx_attrs(src, literals, m.end(), end - 1)
        for attr in STRING_ATTRS:
            if attr in attrs:
                v = literal_value(attrs[attr][0])
                if v and LETTER.search(v):
                    hits.append((attrs[attr][1], "hardcoded-string"))
        low = name.lower()
        if low == "img" and "alt" not in attrs:
            hits.append((m.start(), "a11y-basic"))
        if low in ("div", "span") and "onClick" in attrs:
            hits.append((m.start(), "a11y-basic"))
        if low in ("input", "select", "textarea"):
            typ = literal_value(attrs.get("type", (None, 0))[0]) or ""
            raw_id = attrs.get("id", (None, 0))[0]
            idv = literal_value(raw_id)
            if idv is None and raw_id and re.fullmatch(r"\{\s*[\w.$]+\s*\}", raw_id):
                idv = "{" + raw_id.strip()[1:-1].strip() + "}"
            ln = src.count("\n", 0, m.start())
            before = "\n".join(lines[max(0, ln - 1):ln]) + "\n" + src[src.rfind("\n", 0, m.start()) + 1:m.start()]
            labelled = ("aria-label" in attrs or "aria-labelledby" in attrs
                        or typ.lower() in ("hidden", "submit", "button")
                        or (idv and idv in html_for) or "<label" in before)
            if not labelled:
                hits.append((m.start(), "a11y-basic"))
        if not self_closing and jsx_text_has_letters(masked, end):
            hits.append((end, "hardcoded-string"))
    return hits


VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param",
        "source", "track", "wbr", "!doctype"}
OPTIONAL_CLOSE = {"p", "li", "dt", "dd", "tr", "td", "th", "thead", "tbody", "tfoot", "option",
                  "optgroup", "colgroup", "caption", "rp", "rt"}
IMPLICIT_ROOTS = {"html", "body", "head"}
FIELDS = {"input", "select", "textarea"}
TEMPLATE_EXPR = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{[^{}]*\}", re.S)


class _HtmlLinter(html.parser.HTMLParser):
    def __init__(self, check_parse):
        super().__init__(convert_charrefs=True)
        self.check_parse = check_parse
        self.stack = []  # (tag, line, has_i18n)
        self.hits = []  # (line, rule)
        self.fields = []  # (line, id, labelled)
        self.label_for = set()
        self.raw = None

    def _open(self, tag, attrs, void):
        line = self.getpos()[0]
        a = dict(attrs)
        if "style" in a:
            self.hits.append((line, "inline-style"))
        listed = {part.split(":", 1)[0].strip() for part in (a.get("data-i18n-attr") or "").split(";")}
        for attr in STRING_ATTRS:
            v = a.get(attr)
            if v and LETTER.search(v) and attr not in listed:
                self.hits.append((line, "hardcoded-string"))
        if tag == "img" and "alt" not in a:
            self.hits.append((line, "a11y-basic"))
        if tag in ("div", "span") and "onclick" in a:
            self.hits.append((line, "a11y-basic"))
        if tag == "label" and a.get("for"):
            self.label_for.add(a["for"])
        if tag in FIELDS and (a.get("type") or "").lower() not in ("hidden", "submit", "button", "reset"):
            labelled = ("aria-label" in a or "aria-labelledby" in a
                        or any(t == "label" for t, _, _ in self.stack))
            self.fields.append((line, a.get("id"), labelled))
        if tag in ("script", "style") and not void:
            self.raw = tag
        if not void:
            if tag in OPTIONAL_CLOSE and self.stack and self.stack[-1][0] == tag:
                self.stack.pop()
            self.stack.append((tag, line, "data-i18n" in a))

    def handle_starttag(self, tag, attrs):
        self._open(tag, attrs, tag in VOID)

    def handle_startendtag(self, tag, attrs):
        self._open(tag, attrs, True)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.raw = None
        if not any(t == tag for t, _, _ in self.stack):
            return
        while self.stack:
            t, line, _ = self.stack.pop()
            if t == tag:
                break
            if self.check_parse and t not in OPTIONAL_CLOSE:
                self.hits.append((line, "html-parse"))

    def handle_data(self, data):
        if self.raw:
            return
        text = TEMPLATE_EXPR.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), data)
        m = LETTER.search(text)
        if not m or any(i18n for _, _, i18n in self.stack):
            return
        self.hits.append((self.getpos()[0] + text.count("\n", 0, m.start()), "hardcoded-string"))

    def finish(self):
        self.close()
        if self.check_parse and not any(t in IMPLICIT_ROOTS for t, _, _ in self.stack):
            self.hits += [(line, "html-parse") for t, line, _ in self.stack if t not in OPTIONAL_CLOSE]
        for line, fid, labelled in self.fields:
            if not labelled and not (fid and fid in self.label_for):
                self.hits.append((line, "a11y-basic"))
        return self.hits


def lint_html(path, text, line_offset=0, check_parse=True):
    """Lint markup text; returns [{"file","line","rule","text"}] with lines offset."""
    if text.startswith("---"):
        end = re.search(r"^---[ \t]*$", text[3:], re.M)
        if end:
            cut = 3 + end.end()
            text = re.sub(r"[^\n]", " ", text[:cut]) + text[cut:]
    linter = _HtmlLinter(check_parse)
    linter.feed(text)
    hits = linter.finish()
    lines = text.split("\n")
    return [{"file": str(path), "line": ln + line_offset, "rule": rule,
             "text": (lines[ln - 1] if ln <= len(lines) else "").strip()[:MAX_TEXT]}
            for ln, rule in sorted(hits)]


def html_js_findings(src, skip_colors):
    """web-html .js/.mjs: literal colors/physical, plus HTML inside template literals."""
    masked, literals = scan_js(src)
    hits = js_literal_findings(src, masked, literals, skip_colors)
    extra = []
    for a, b in literals.items():
        if src[a] == "`" and "<" in src[a + 1:b - 1]:
            extra += lint_html("", src[a + 1:b - 1], src.count("\n", 0, a), check_parse=False)
    return hits, extra


def web_lint_file(path, platform, skip_colors):
    src = Path(path).read_text(encoding="utf-8", errors="replace")
    lower = str(path).lower()
    lines = src.split("\n")
    found, hits = [], []
    if lower.endswith((".css", ".scss")):
        masked = mask_css(src, lower.endswith(".scss"))
        hits = css_findings(masked, 0, skip_colors)
    elif platform == "web-react":
        hits = react_findings(src, skip_colors)
    elif lower.endswith((".js", ".mjs")):
        hits, extra = html_js_findings(src, skip_colors)
        found += extra
    else:
        found += lint_html(path, src)
    for f in found:
        f["file"] = str(path)
        f["text"] = lines[f["line"] - 1].strip()[:MAX_TEXT] if f["line"] <= len(lines) else ""
    found = [f for f in found if IGNORE_MARKER not in (lines[f["line"] - 1] if f["line"] <= len(lines) else "")]
    for off, rule in sorted(hits):
        ln = src.count("\n", 0, off) + 1
        text = lines[ln - 1] if ln <= len(lines) else ""
        if IGNORE_MARKER in text:
            continue
        found.append({"file": str(path), "line": ln, "rule": rule, "text": text.strip()[:MAX_TEXT]})
    return found


WEB_PLATFORMS = ("web-react", "web-html")
PLATFORMS = sorted(set(RULES) | set(WEB_PLATFORMS))


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Lint generated code for hard-coded colors and user-facing strings. "
                    "Prints JSON findings; exits 1 if there are any.")
    p.add_argument("--platform", required=True, help="target platform (supported: %s)" % ", ".join(PLATFORMS))
    p.add_argument("--allow", action="append", default=[], metavar="GLOB",
                   help="extra glob of files to skip, added to the platform defaults (repeatable)")
    p.add_argument("--allow-colors", action="append", default=[], metavar="GLOB",
                   help="glob of token files where color literals are allowed; other rules "
                        "still apply (repeatable)")
    p.add_argument("files", nargs="*", help="files to lint")
    args = p.parse_args(argv)

    if args.platform not in PLATFORMS:
        print(f"unknown platform: {args.platform} (supported: {', '.join(PLATFORMS)})", file=sys.stderr)
        return 2
    for f in args.files:
        if not Path(f).is_file():
            print(f"file not found: {f}", file=sys.stderr)
            return 2

    globs = [glob_to_regex(g) for g in DEFAULT_ALLOW.get(args.platform, []) + args.allow]
    color_globs = [glob_to_regex(g) for g in args.allow_colors]
    exts = EXTENSIONS[args.platform]
    findings = []
    for f in sorted(set(args.files)):
        if not f.endswith(exts) or is_allowed(f, globs):
            continue
        if args.platform in WEB_PLATFORMS:
            findings.extend(web_lint_file(f, args.platform, is_allowed(f, color_globs)))
            continue
        rules = RULES[args.platform]
        if is_allowed(f, color_globs):
            rules = [r for r in rules if r[0] != "hardcoded-color"]
        findings.extend(lint_file(f, rules))
    findings.sort(key=lambda x: (x["file"], x["line"]))
    print(json.dumps({"version": 1, "findings": findings}, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
