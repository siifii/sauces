"""Headless tests for the scaffold skill (marker: skill), Flutter create mode."""
import json
import subprocess

import pytest

from conftest import fixture_copy, needs_claude, needs_flutter, run_skill

pytestmark = [pytest.mark.skill, needs_claude, needs_flutter]


def snapshot(root):
    """{relative path: bytes} for every file outside .git/ and .sauces/."""
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and not {".git", ".sauces"} & set(p.relative_to(root).parts)
    }


@pytest.fixture(scope="module")
def scaffolded(tmp_path_factory):
    workdir = fixture_copy("empty", tmp_path_factory.mktemp("scaffold"))
    result = run_skill(workdir, "/sauces:scaffold flutter")
    log = f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert result.returncode == 0, log
    return workdir, log


def test_scaffold_empty(scaffolded):
    workdir, log = scaffolded
    app = workdir / "flutter"
    assert (app / "pubspec.yaml").is_file(), log
    assert (app / "lib" / "l10n" / "app_ar.arb").is_file(), log
    for cmd in (["flutter", "analyze", "--no-fatal-infos"], ["flutter", "test"]):
        run = subprocess.run(cmd, cwd=app, capture_output=True, text=True)
        assert run.returncode == 0, f"{' '.join(cmd)}\n{run.stdout}\n{run.stderr}\n{log}"


def test_scaffold_rescans_as_existing(scaffolded):
    workdir, log = scaffolded
    profile = json.loads((workdir / ".sauces" / "project-profile.json").read_text())
    assert profile["mode"] == "existing", (profile, log)
    roots = {p["root"] for p in profile["projects"] if p["platform"] == "flutter"}
    assert roots == {"flutter"}, (profile, log)


def test_scaffold_refuses_non_empty(tmp_path):
    workdir = fixture_copy("empty", tmp_path)
    (workdir / "notes.txt").write_text("my notes\n")
    before = snapshot(workdir)
    result = run_skill(workdir, "/sauces:scaffold flutter")
    out = result.stdout + result.stderr
    assert snapshot(workdir) == before, out
    assert not (workdir / "flutter").exists(), out
    assert "not empty" in out.lower(), out
