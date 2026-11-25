"""Headless tests for the cook skill (marker: skill): the whole pipeline, then reruns.

The tests share one module-scoped flutter-bloc copy and run in file order: the
end-to-end run first, then the idempotent rerun and the changed-input rerun.
"""
import json
import subprocess

import pytest
from PIL import Image

from conftest import fixture_copy, needs_claude, needs_flutter, run_skill
from test_build import copy_design

pytestmark = [pytest.mark.skill, needs_claude, needs_flutter]
COOK_TIMEOUT = 3600  # a full cook (scan to report) can take longer than run_skill's default


def git_status(workdir):
    return subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                          cwd=workdir, capture_output=True, text=True, check=True).stdout


def contents(workdir):
    """{path: bytes} for every file outside .git/, .dart_tool/ and build/."""
    skip = {".git", ".dart_tool", "build"}
    return {
        str(p.relative_to(workdir)): p.read_bytes()
        for p in sorted(workdir.rglob("*"))
        if p.is_file() and not skip & set(p.relative_to(workdir).parts)
        and p.name != "eval-approve"
    }


def state(workdir):
    return json.loads((workdir / ".sauces" / "state.json").read_text())


def cook(workdir, design):
    result = run_skill(workdir, f'/sauces:cook "{design}"', timeout=COOK_TIMEOUT)
    log = f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert result.returncode == 0, log
    return result.stdout + result.stderr, log


@pytest.fixture(scope="module")
def cooked(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("cook")
    workdir = fixture_copy("flutter-bloc", tmp)
    design = copy_design(tmp / "design")
    _, log = cook(workdir, design)
    return {"workdir": workdir, "design": design, "log": log, "status": git_status(workdir),
            "contents": contents(workdir)}


def test_cook_flutter_end_to_end(cooked):
    workdir, log = cooked["workdir"], cooked["log"]
    assert (workdir / ".sauces" / "report.html").is_file(), log
    stages = state(workdir)["stages"]
    assert {s: v["status"] for s, v in stages.items()} == {s: "done" for s in stages}, log
    summary = json.loads((workdir / ".sauces" / "verify" / "summary.json").read_text())
    default = next(r for r in summary["results"] if r["id"] == "login--default")
    assert default["score"] >= 90, (default, log)
    assert not (workdir / ".sauces" / "eval-approve").exists(), "eval-approve must be single-use"


def no_duplicate_keys(pairs):
    keys = [k for k, _ in pairs]
    dupes = {k for k in keys if keys.count(k) > 1}
    assert not dupes, dupes
    return dict(pairs)


def test_cook_rerun_is_idempotent(cooked):
    workdir, design = cooked["workdir"], cooked["design"]
    out, log = cook(workdir, design)
    assert "nothing to do" in out.lower(), log
    assert git_status(workdir) == cooked["status"], log
    after = contents(workdir)
    changed = sorted(k for k in after.keys() | cooked["contents"].keys()
                     if after.get(k) != cooked["contents"].get(k))
    assert not changed, (changed, log)

    ingest_before = state(workdir)["stages"]["ingest"]["finished_at"]
    png = design / "login--error.png"
    with Image.open(png) as im:
        im = im.convert("RGBA")
        r, g, b, a = im.getpixel((0, 0))
        im.putpixel((0, 0), ((r + 1) % 256, g, b, a))
        im.save(png)
    _, log = cook(workdir, design)
    after = state(workdir)
    assert after["stages"]["ingest"]["finished_at"] != ingest_before, log
    for arb in sorted((workdir / "lib" / "l10n").glob("*.arb")):
        json.loads(arb.read_text(), object_pairs_hook=no_duplicate_keys)
    for key in ("generated_files", "changed_files"):
        assert len(after[key]) == len(set(after[key])), (key, after[key])
