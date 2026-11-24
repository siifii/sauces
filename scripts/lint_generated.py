#!/usr/bin/env python3
"""Lint generated UI code for hard-coded colors and user-facing strings (Sauces).

Stdlib only. Usage: lint_generated.py --platform flutter [--allow GLOB ...] files...

Prints {"version":1,"findings":[{"file","line","rule","text"}]} on stdout.
Exit codes: 0 clean, 1 findings, 2 usage error (unknown platform, missing file).

Comments are blanked (line numbers preserved) before matching, so commented-out
code never flags. A `// sauces-lint-ignore` comment on a line suppresses findings
that start on that line. Files matching an allow glob are skipped; --allow globs
are added to the platform defaults.

Known limit: the hardcoded-string rule only sees a literal that is the first
argument of Text()/SelectableText() or the value of a named label argument,
so `Text(cond ? 'a' : 'b')` is not flagged.
"""
import argparse
import json
import re
import sys
from pathlib import Path

IGNORE_MARKER = "sauces-lint-ignore"
MAX_TEXT = 200

_STRING_ARGS = r"(?:hintText|labelText|helperText|errorText|tooltip|semanticsLabel)"

# RULES[platform] -> [(rule_id, regex)]. A regex with a named group `lit` points at the
# start of a string literal; the finding is dropped when that literal is empty.
RULES = {
    "flutter": [
        ("hardcoded-color", re.compile(
            r"Color\(0x|Color\.fromARGB|Color\.fromRGBO|\bColors\.(?!transparent\b)")),
        ("hardcoded-string", re.compile(
            r"(?:\b(?:Text|SelectableText)\(\s*|\b" + _STRING_ARGS + r":\s*)"
            r"(?P<lit>r?(?:'|\"))")),
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


def lint_file(path, rules):
    src = Path(path).read_text(encoding="utf-8", errors="replace")
    masked, literals = scan(src)
    lines = src.splitlines()
    def line_of(pos):
        return masked.count("\n", 0, pos) + 1

    found = []
    for rule_id, rx in rules:
        for m in rx.finditer(masked):
            if inside_literal(m.start(), literals):
                continue
            if "lit" in rx.groupindex:
                end = literals.get(m.start("lit"))
                if end is None:
                    continue
                body = src[m.start("lit"):end].lstrip("r")
                if body in ("''", '""', "", '""""""'):
                    continue  # empty literal
            ln = line_of(m.start())
            text = lines[ln - 1] if ln <= len(lines) else ""
            if IGNORE_MARKER in text:
                continue
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
    exts = EXTENSIONS[args.platform]
    findings = []
    for f in sorted(set(args.files)):
        if not f.endswith(exts) or is_allowed(f, globs):
            continue
        findings.extend(lint_file(f, RULES[args.platform]))
    findings.sort(key=lambda x: (x["file"], x["line"]))
    print(json.dumps({"version": 1, "findings": findings}, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
