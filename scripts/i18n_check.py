#!/usr/bin/env python3
"""Check that a translated catalog keeps the source catalog's placeholders (Sauces).

For every key present in both catalogs, the multiset of placeholders must match:
{name}, {{name}}, ${x}, $name, printf (%s, %d, %1$s, %@) and ICU arguments. For ICU
plural/select messages the argument name, the type and the `other` branch must be kept;
branch selectors may differ between languages (Arabic adds zero/two/few/many). Keys that
are plural forms other than `other` (`key.one`, `key_few`, Android plural items) are not
compared: a language may drop the number there ("one order").

Formats (by extension): .json (flat or nested), .arb (@-keys ignored), .xml (Android
strings.xml: <string> and <plurals> items keyed name / name[quantity]).

Stdlib only. Usage: i18n_check.py SOURCE TARGET
Prints {"problems": [{"key", "expected", "found"}], "missing": [keys]} on stdout.
Exit codes: 0 all shared keys match, 1 placeholder problems, 2 usage error.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

SIMPLE = re.compile(r"\{\{\s*[\w.]+\s*\}\}|\$\{[^{}]*\}|%(?:\d+\$)?[-+ #0]*\d*(?:\.\d+)?[sdifuxXeEgGc@]"
                    r"|\$[A-Za-z_]\w*")
ICU = re.compile(r"\{\s*([A-Za-z_]\w*)\s*(?:,\s*(plural|select|selectordinal)\s*,)?")


def matching(s, i):
    depth = 0
    for j in range(i, len(s)):
        depth += {"{": 1, "}": -1}.get(s[j], 0)
        if depth == 0:
            return j
    return len(s) - 1


def placeholders(msg):
    """Counter of placeholder signatures in a message."""
    found = Counter(m.group().replace(" ", "") for m in SIMPLE.finditer(msg))
    i = 0
    while i < len(msg):
        if msg.startswith("{{", i):
            i = msg.find("}}", i) + 2 or len(msg)
            continue
        if msg[i] == "{" and not (i and msg[i - 1] == "$"):
            m = ICU.match(msg, i)
            end = matching(msg, i)
            if m:
                name, kind = m.group(1), m.group(2)
                if kind:
                    body = msg[m.end():end]
                    branches = set(re.findall(r"(=?\w+)\s*\{", body))
                    found[f"{{{name},{kind},other={'other' in branches}}}"] += 1
                    # placeholders nested inside branches count once per message
                    inner = Counter()
                    k = 0
                    while k < len(body):
                        if body[k] == "{":
                            e = matching(body, k)
                            inner |= placeholders(body[k + 1:e])
                            k = e + 1
                        else:
                            k += 1
                    found |= inner
                else:
                    found[f"{{{name}}}"] += 1
            i = end + 1
            continue
        i += 1
    return found


def flatten(value, prefix=""):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else k))
        return out
    return {prefix: value} if isinstance(value, str) else {}


PLURAL_FORM = re.compile(r"[._](?:zero|one|two|few|many)$")

ITEM = re.compile(r'<string\s+name="([^"]+)"([^>]*)>(.*?)</string>'
                  r'|<plurals\s+name="([^"]+)"[^>]*>(.*?)</plurals>', re.S)
PLURAL_ITEM = re.compile(r'<item\s+quantity="([^"]+)"[^>]*>(.*?)</item>', re.S)


def load(path):
    text = path.read_text(encoding="utf-8")
    name = path.name.lower()
    if name.endswith(".arb"):
        return {k: v for k, v in json.loads(text).items() if not k.startswith("@") and isinstance(v, str)}
    if name.endswith(".json"):
        return flatten(json.loads(text))
    if name.endswith(".xml"):
        out = {}
        for m in ITEM.finditer(text):
            if m.group(1):
                if 'translatable="false"' not in m.group(2):
                    out[m.group(1)] = m.group(3)
            else:
                for q in PLURAL_ITEM.finditer(m.group(5)):
                    out[f"{m.group(4)}[{q.group(1)}]"] = q.group(2)
        return out
    raise ValueError(f"unknown catalog format: {path}")


def main(argv=None):
    p = argparse.ArgumentParser(description="Check that a translated catalog keeps the source's placeholders.")
    p.add_argument("source", type=Path)
    p.add_argument("target", type=Path)
    args = p.parse_args(argv)
    try:
        src, tgt = load(args.source), load(args.target)
    except (OSError, ValueError) as err:
        print(str(err), file=sys.stderr)
        return 2
    problems = []
    for key, msg in src.items():
        if key not in tgt:
            continue
        if "[" in key and key.endswith("]"):  # Android plural items: quantities differ by language
            continue
        if PLURAL_FORM.search(key):  # key.one / key_few: languages may drop the number there
            continue
        want, got = placeholders(msg), placeholders(tgt[key])
        if want != got:
            problems.append({"key": key, "expected": sorted(want.elements()), "found": sorted(got.elements())})
    missing = sorted(k for k in src if k not in tgt and not ("[" in k and k.endswith("]")))
    print(json.dumps({"problems": problems, "missing": missing}, ensure_ascii=False, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
