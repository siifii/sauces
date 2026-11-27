#!/usr/bin/env python3
"""Make a pseudo-locale copy of a string catalog (Sauces).

Pseudo-localization swaps letters for accented look-alikes, pads each message by about 30%
and wraps it in [brackets], so a render in the pseudo-locale shows at a glance:
text that is hard-coded (it stays plain), text that is clipped (a bracket is missing), and
layouts that cannot take longer translations.

Placeholders are kept exactly: {name}, {{name}}, ${x}, $name, %s, %d, %1$s, %@, and ICU
messages ({count, plural, one {...} other {...}}) keep their syntax while the text inside
each branch is transformed (# stays). HTML/XML tags and entities are kept.

Formats (by extension, or --format): json (flat or nested, i18next/next-intl/locales/*.json),
arb (Flutter: @-keys copied unchanged, @@locale set to --locale), android-xml
(res/values/strings.xml: <string> and <plurals>/<string-array> items; translatable="false"
skipped).

Stdlib only. Usage: pseudo_locale.py CATALOG --out OUT [--format F] [--locale en-XA] [--expand 0.3]
Exit codes: 0 written, 2 usage error (unknown format, unreadable input).
"""
import argparse
import json
import re
import sys
from pathlib import Path

ACCENTS = str.maketrans(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "àƀçđéƒĝĥîĵķļɱñöþǫŕšţûṽŵẋýžÀßÇÐÉƑĜĤÎĴĶĻṀÑÖÞǪŔŠŢÛṼŴẊÝŽ",
)
# Kept verbatim: {{x}}, ${x}, simple {x}, printf (%1$s %d %@ %%), $name, tags, entities, \n.
PROTECTED = re.compile(
    r"\{\{[^{}]*\}\}|\$\{[^{}]*\}|%(?:\d+\$)?[-+ #0]*\d*(?:\.\d+)?[sdifuxXeEgGc@%]"
    r"|\$[A-Za-z_]\w*|<[^<>]+>|&[#\w]+;|\\[nt\"']")
ICU_HEAD = re.compile(r"\s*([A-Za-z_]\w*)\s*,\s*(plural|select|selectordinal)\s*,", re.S)


def pad(n_letters, expand):
    return "~" * max(1, round(n_letters * expand))


def accent_text(text):
    """Accent plain text, leaving protected tokens unchanged."""
    out, last = [], 0
    for m in PROTECTED.finditer(text):
        out.append(text[last:m.start()].translate(ACCENTS))
        out.append(m.group())
        last = m.end()
    out.append(text[last:].translate(ACCENTS))
    return "".join(out)


def matching_brace(s, i):
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return j
    return -1


def transform_message(s):
    """Accent a message, recursing into ICU plural/select branches."""
    out, i = [], 0
    while i < len(s):
        if s.startswith("{{", i) or s.startswith("${", i):
            j = s.find("}}", i) + 2 if s.startswith("{{", i) else s.find("}", i) + 1
            if j <= 0:
                out.append(accent_text(s[i:]))
                break
            out.append(s[i:j])
            i = j
            continue
        if s[i] == "{":
            j = matching_brace(s, i)
            if j < 0:
                out.append(accent_text(s[i:]))
                break
            inner = s[i + 1:j]
            head = ICU_HEAD.match(inner)
            if head:
                out.append("{" + inner[:head.end()] + transform_branches(inner[head.end():]) + "}")
            else:
                out.append(s[i:j + 1])  # simple placeholder {name}
            i = j + 1
            continue
        k = i
        while k < len(s) and s[k] != "{" and not s.startswith("${", k):
            k += 1
        out.append(accent_text(s[i:k]))
        i = k
    return "".join(out)


def transform_branches(rest):
    out, i = [], 0
    while i < len(rest):
        b = rest.find("{", i)
        if b < 0:
            out.append(rest[i:])
            break
        out.append(rest[i:b])  # selector such as " one " or " =0 "
        e = matching_brace(rest, b)
        if e < 0:
            out.append(rest[b:])
            break
        out.append("{" + transform_message(rest[b + 1:e]) + "}")
        i = e + 1
    return "".join(out)


def pseudo(message, expand):
    if not isinstance(message, str) or not message.strip():
        return message
    letters = sum(c.isalpha() for c in PROTECTED.sub("", message))
    return "[" + transform_message(message) + pad(letters, expand) + "]"


def walk(value, expand):
    if isinstance(value, dict):
        return {k: walk(v, expand) for k, v in value.items()}
    if isinstance(value, list):
        return [walk(v, expand) for v in value]
    return pseudo(value, expand)


def do_json(text, expand, locale):
    return json.dumps(walk(json.loads(text), expand), ensure_ascii=False, indent=2) + "\n"


def do_arb(text, expand, locale):
    data = json.loads(text)
    out = {}
    for k, v in data.items():
        if k == "@@locale":
            out[k] = locale.replace("-", "_")
        elif k.startswith("@"):
            out[k] = v
        else:
            out[k] = pseudo(v, expand)
    return json.dumps(out, ensure_ascii=False, indent=2) + "\n"


XML_ITEM = re.compile(r"(<(string|item)\b([^>]*)>)(.*?)(</\2>)", re.S)


def do_android_xml(text, expand, locale):
    def repl(m):
        if 'translatable="false"' in m.group(3):
            return m.group(0)
        return m.group(1) + pseudo(m.group(4), expand) + m.group(5)
    return XML_ITEM.sub(repl, text)


FORMATS = {"json": do_json, "arb": do_arb, "android-xml": do_android_xml}


def detect(path):
    name = path.name.lower()
    if name.endswith(".arb"):
        return "arb"
    if name.endswith(".json"):
        return "json"
    if name.endswith(".xml"):
        return "android-xml"
    return None


def main(argv=None):
    p = argparse.ArgumentParser(description="Write a pseudo-locale copy of a string catalog "
                                "(accented, ~30%% longer, [bracketed]; placeholders kept).")
    p.add_argument("catalog", type=Path, help="source catalog (.json, .arb, strings.xml)")
    p.add_argument("--out", required=True, type=Path, help="where to write the pseudo catalog")
    p.add_argument("--format", choices=sorted(FORMATS), help="override format detection")
    p.add_argument("--locale", default="en-XA", help="pseudo-locale tag (ARB @@locale); default en-XA")
    p.add_argument("--expand", type=float, default=0.3, help="padding ratio; default 0.3")
    args = p.parse_args(argv)
    fmt = args.format or detect(args.catalog)
    if fmt is None:
        print(f"unknown catalog format: {args.catalog} (use --format)", file=sys.stderr)
        return 2
    try:
        text = args.catalog.read_text(encoding="utf-8")
        result = FORMATS[fmt](text, args.expand, args.locale)
    except (OSError, ValueError) as err:
        print(f"cannot read {args.catalog}: {err}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(result, encoding="utf-8")
    print(json.dumps({"format": fmt, "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
