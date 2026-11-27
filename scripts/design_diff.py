#!/usr/bin/env python3
"""Compare two Sauces design snapshots and write design-diff.json (Sauces).

Each snapshot folder holds manifest.json and references/. States are keyed
<screen>--<state>. A state is `changed` when its reference size differs or the mean
absolute pixel difference exceeds 0.5%. Tokens match by name (colors, typography) or by
value (spacing, radii); copy is the text values in each state's layout.

Exit codes: 0 ok, 2 unreadable input, 3 missing dependency.
"""
import argparse
import json
import sys
from pathlib import Path

THRESHOLD = 0.5  # percent of full scale


def require_deps() -> None:
    """Exit 3 with an install hint if Pillow or numpy is missing."""
    for module, name in (("PIL", "PIL"), ("numpy", "numpy")):
        try:
            __import__(module)
        except ImportError:
            print(f"Missing dependency: {name}. Install with: python3 -m pip install pillow numpy",
                  file=sys.stderr)
            raise SystemExit(3)


def fail(message):
    print(message, file=sys.stderr)
    raise SystemExit(2)


def load_manifest(folder):
    path = Path(folder) / "manifest.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        fail(f"Cannot read {path}: {exc}")
    if not isinstance(data, dict):
        fail(f"{path}: expected a JSON object")
    return data


def state_map(manifest):
    found = {}
    for screen in manifest.get("screens") or []:
        for state in screen.get("states") or []:
            found[f"{screen.get('id')}--{state.get('id')}"] = state
    return found


def texts(node):
    """Every `text` value in a layout tree, in order, without duplicates."""
    found = []

    def walk(n):
        if isinstance(n, dict):
            if isinstance(n.get("text"), str) and n["text"] not in found:
                found.append(n["text"])
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)

    walk(node)
    return found


def compare_reference(old_dir, new_dir, old_state, new_state):
    import numpy as np
    from PIL import Image

    def ref(folder, state):
        return Path(folder) / "references" / Path(str(state.get("reference") or "")).name

    a, b = ref(old_dir, old_state), ref(new_dir, new_state)
    for path in (a, b):
        if not path.is_file():
            return "changed", f"reference missing: {path.name}"
    with Image.open(a) as ia, Image.open(b) as ib:
        if ia.size != ib.size:
            return "changed", f"size {ia.size[0]}x{ia.size[1]} -> {ib.size[0]}x{ib.size[1]}"
        x = np.asarray(ia.convert("RGB"), dtype=np.int16)
        y = np.asarray(ib.convert("RGB"), dtype=np.int16)
    percent = float(np.abs(x - y).mean()) / 255 * 100
    if percent > THRESHOLD:
        return "changed", f"{percent:.2f}% pixel difference"
    return "unchanged", f"{percent:.2f}% pixel difference"


def diff_states(old_dir, new_dir, old, new):
    old_states, new_states = state_map(old), state_map(new)
    result = []
    for sid in sorted(set(old_states) | set(new_states)):
        if sid not in new_states:
            result.append({"id": sid, "status": "removed", "reason": "state is not in the new design"})
        elif sid not in old_states:
            result.append({"id": sid, "status": "added", "reason": "state is new in the design"})
        else:
            status, reason = compare_reference(old_dir, new_dir, old_states[sid], new_states[sid])
            result.append({"id": sid, "status": status, "reason": reason})
    return result


def by_key(items, key):
    return {key(i): i for i in items if isinstance(i, dict)}


def diff_named(old_items, new_items, fields):
    """Added/removed/changed for tokens matched by name (else hex)."""
    key = lambda i: i.get("name") or i.get("hex")
    o, n = by_key(old_items, key), by_key(new_items, key)
    changed = [n[k] for k in n if k in o and any(o[k].get(f) != n[k].get(f) for f in fields)]
    return {"added": [n[k] for k in n if k not in o],
            "removed": [o[k] for k in o if k not in n],
            "changed": changed}


def values(items):
    return [i["value"] if isinstance(i, dict) else i for i in items or []]


def diff_values(old_items, new_items):
    o, n = values(old_items), values(new_items)
    return {"added": [v for v in n if v not in o], "removed": [v for v in o if v not in n], "changed": []}


def diff_copy(old_states, new_states):
    out = {"added": [], "removed": [], "changed": []}
    for sid in sorted(set(old_states) & set(new_states)):
        o, n = texts(old_states[sid].get("layout")), texts(new_states[sid].get("layout"))
        gone, new = [t for t in o if t not in n], [t for t in n if t not in o]
        if gone and len(gone) == len(new):
            out["changed"] += [{"state": sid, "old": a, "new": b} for a, b in zip(gone, new)]
        else:
            out["removed"] += [{"state": sid, "text": t} for t in gone]
            out["added"] += [{"state": sid, "text": t} for t in new]
    return out


def build(old_dir, new_dir):
    old, new = load_manifest(old_dir), load_manifest(new_dir)
    ot, nt = old.get("tokens") or {}, new.get("tokens") or {}
    states = diff_states(old_dir, new_dir, old, new)
    summary = {k: sum(1 for s in states if s["status"] == k) for k in ("changed", "added", "removed", "unchanged")}
    return {
        "states": states,
        "tokens": {
            "colors": diff_named(ot.get("colors") or [], nt.get("colors") or [], ("hex",)),
            "typography": diff_named(ot.get("typography") or [], nt.get("typography") or [],
                                     ("size", "weight", "line_height", "family")),
            "spacing": diff_values(ot.get("spacing"), nt.get("spacing")),
            "radii": diff_values(ot.get("radii"), nt.get("radii")),
        },
        "copy": diff_copy(state_map(old), state_map(new)),
        "assets": diff_named(old.get("assets") or [], new.get("assets") or [], ("path", "kind")),
        "summary": summary,
    }


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="design_diff.py",
        description="Compare two Sauces design snapshots (manifest.json + references/) and write design-diff.json.")
    p.add_argument("--old", required=True, help="folder with the previous manifest.json and references/")
    p.add_argument("--new", required=True, help="folder with the new manifest.json and references/")
    p.add_argument("-o", "--output", required=True, help="where to write design-diff.json")
    args = p.parse_args(argv)
    require_deps()
    data = build(args.old, args.new)
    Path(args.output).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    s = data["summary"]
    print(f"{s['changed']} changed, {s['added']} added, {s['removed']} removed, {s['unchanged']} unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
