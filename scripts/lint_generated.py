#!/usr/bin/env python3
"""Lint generated UI code for hard-coded colors and user-facing strings (Sauces).

Stdlib only. Usage: lint_generated.py --platform flutter [--allow GLOB ...]
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
"""
import argparse
import json
import re
import sys
from pathlib import Path

IGNORE_MARKER = "sauces-lint-ignore"
MAX_TEXT = 200

_STRING_ARGS = r"(?:hintText|labelText|helperText|errorText|tooltip|semanticsLabel)"

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
}
EXTENSIONS = {"flutter": (".dart",)}
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


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Lint generated code for hard-coded colors and user-facing strings. "
                    "Prints JSON findings; exits 1 if there are any.")
    p.add_argument("--platform", required=True, help="target platform (supported: %s)" % ", ".join(sorted(RULES)))
    p.add_argument("--allow", action="append", default=[], metavar="GLOB",
                   help="extra glob of files to skip, added to the platform defaults (repeatable)")
    p.add_argument("--allow-colors", action="append", default=[], metavar="GLOB",
                   help="glob of token files where color literals are allowed; other rules "
                        "still apply (repeatable)")
    p.add_argument("files", nargs="*", help="files to lint")
    args = p.parse_args(argv)

    if args.platform not in RULES:
        print(f"unknown platform: {args.platform} (supported: {', '.join(sorted(RULES))})", file=sys.stderr)
        return 2
    for f in args.files:
        if not Path(f).is_file():
            print(f"file not found: {f}", file=sys.stderr)
            return 2

    globs = [glob_to_regex(g) for g in DEFAULT_ALLOW[args.platform] + args.allow]
    color_globs = [glob_to_regex(g) for g in args.allow_colors]
    exts = EXTENSIONS[args.platform]
    findings = []
    for f in sorted(set(args.files)):
        if not f.endswith(exts) or is_allowed(f, globs):
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
