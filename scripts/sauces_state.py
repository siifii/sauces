#!/usr/bin/env python3
"""Track pipeline progress in <root>/.sauces/state.json (Sauces).

Stdlib only. Subcommands:
  hash <paths...>                  print one sha256 over the sorted (path, bytes)
                                   pairs; folders are walked, .DS_Store and
                                   .sauces/ are skipped
  mark <stage> [--inputs-hash H]   set a stage to done (H required for ingest).
                                   Marking ingest with a hash different from the
                                   stored one resets scan..report to pending.
  next --inputs-hash H             print the stage to resume at, or `done`
  reset-from <stage>               set that stage and all later ones to pending
  add-files generated|changed <paths...>
                                   append to generated_files / changed_files

Hash keys: a folder argument contributes `<folder basename>/<posix relative
path>` per file, a file argument contributes its basename. Keys do not depend
on where the project lives, so moving it keeps the hash.

Stages: ingest, scan, plan, build, verify, report. Only ingest is keyed on the
design sources hash; a changed hash restarts the pipeline at ingest.

Exit codes: 0 ok, 2 usage error (unknown stage, missing hash, missing path).
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

STAGES = ["ingest", "scan", "plan", "build", "verify", "report"]


def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


def blank_stage():
    return {"status": "pending", "finished_at": None, "inputs_hash": None}


def state_path(root):
    return Path(root) / ".sauces" / "state.json"


def load(root):
    p = state_path(root)
    if p.exists():
        try:
            st = json.loads(p.read_text())
        except ValueError:
            fail(f"state.json is not valid JSON: {p}")
    else:
        st = {}
    st["version"] = 1
    stages = st.setdefault("stages", {})
    for s in STAGES:
        stages.setdefault(s, blank_stage())
    st.setdefault("generated_files", [])
    st.setdefault("changed_files", [])
    return st


def save(root, st):
    p = state_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".state-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(st, f, indent=2)
            f.write("\n")
        os.replace(tmp, p)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def check_stage(name):
    if name not in STAGES:
        fail(f"Unknown stage: {name}. Expected one of: {', '.join(STAGES)}")


def collect(arg):
    """Yield (posix key, file path) for one hash argument."""
    p = Path(arg)
    if not p.exists():
        fail(f"Path not found: {arg}")
    if p.is_file():
        yield p.name, p
        return
    base = p.resolve().name
    for dirpath, dirnames, filenames in os.walk(p):
        dirnames[:] = [d for d in dirnames if d != ".sauces"]
        for fn in filenames:
            if fn == ".DS_Store":
                continue
            fp = Path(dirpath) / fn
            yield f"{base}/{fp.relative_to(p).as_posix()}", fp


def cmd_hash(args):
    items = sorted((k, fp) for a in args.paths for k, fp in collect(a))
    h = hashlib.sha256()
    for key, fp in items:
        kb = key.encode()
        h.update(len(kb).to_bytes(8, "big") + kb)
        data = fp.read_bytes()
        h.update(len(data).to_bytes(8, "big") + data)
    print(h.hexdigest())


def cmd_mark(args):
    check_stage(args.stage)
    if args.stage == "ingest" and not args.inputs_hash:
        fail("mark ingest requires --inputs-hash")
    st = load(args.root)
    old = st["stages"]["ingest"]["inputs_hash"]
    if args.stage == "ingest" and old is not None and old != args.inputs_hash:
        for s in STAGES[1:]:
            st["stages"][s] = blank_stage()
    st["stages"][args.stage] = {
        "status": "done",
        "finished_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs_hash": args.inputs_hash,
    }
    save(args.root, st)


def cmd_next(args):
    st = load(args.root)
    ing = st["stages"]["ingest"]
    if ing["status"] != "done" or ing["inputs_hash"] != args.inputs_hash:
        print("ingest")
        return
    for s in STAGES:
        if st["stages"][s]["status"] != "done":
            print(s)
            return
    print("done")


def cmd_reset(args):
    check_stage(args.stage)
    st = load(args.root)
    for s in STAGES[STAGES.index(args.stage):]:
        st["stages"][s] = blank_stage()
    save(args.root, st)


def cmd_add(args):
    st = load(args.root)
    key = f"{args.kind}_files"
    for p in args.paths:
        if p not in st[key]:
            st[key].append(p)
    save(args.root, st)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, **kw):
        sp = sub.add_parser(name, **kw)
        sp.set_defaults(fn=fn)
        if name != "hash":
            sp.add_argument("--root", default=".", help="target project (default .)")
        return sp

    add("hash", cmd_hash, help="sha256 over files/folders (keys: folder basename/relative path; file basename)").add_argument("paths", nargs="+")
    sp = add("mark", cmd_mark, help="mark a stage done")
    sp.add_argument("stage")
    sp.add_argument("--inputs-hash")
    sp = add("next", cmd_next, help="print stage to resume at")
    sp.add_argument("--inputs-hash", required=True)
    add("reset-from", cmd_reset, help="reset a stage and later ones").add_argument("stage")
    sp = add("add-files", cmd_add, help="record generated/changed files")
    sp.add_argument("kind", choices=["generated", "changed"])
    sp.add_argument("paths", nargs="+")

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
