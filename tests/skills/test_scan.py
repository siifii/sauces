"""Headless tests for the scan-project skill (marker: skill)."""
import json
import subprocess

import pytest

from conftest import REPO, fixture_copy, needs_claude, run_script, run_skill

SCHEMA = REPO / "skills" / "scan-project" / "references" / "profile-schema.json"

pytestmark = [pytest.mark.skill, needs_claude]


def git_status(workdir):
    """Porcelain status lines, ignoring Sauces' own .sauces/ working folder."""
    out = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=workdir, capture_output=True, text=True, check=True,
    ).stdout
    return [line for line in out.splitlines() if not line[3:].startswith(".sauces/")]


def scan(workdir):
    before = git_status(workdir)
    result = run_skill(workdir, "/sauces:scan-project")
    profile_path = workdir / ".sauces" / "project-profile.json"
    assert profile_path.is_file(), (
        f"no profile written\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    check = run_script("check_json.py", str(SCHEMA), str(profile_path))
    assert check.returncode == 0, check.stdout + check.stderr
    return before, json.loads(profile_path.read_text()), result


def test_scan_flutter_fixture(tmp_path):
    workdir = fixture_copy("flutter-bloc", tmp_path)
    before, profile, _ = scan(workdir)

    assert profile["mode"] == "existing"
    assert len(profile["projects"]) == 1, profile["projects"]
    project = profile["projects"][0]
    assert project["root"] == "."
    assert project["platform"] == "flutter"
    assert project["state_management"] == "bloc"
    assert project["localization"]["system"] == "arb"
    assert "ar" in project["localization"]["locales"]
    names = {c["name"] for c in project["components"]}
    assert {"AppButton", "AppTextField", "AppCard"} <= names
    color_findings = [f for f in project["findings"] if f["area"] == "colors"]
    assert any("lib/core/widgets/app_card.dart" in f["paths"] for f in color_findings), (
        project["findings"]
    )
    assert git_status(workdir) == before


def test_scan_empty(tmp_path):
    workdir = fixture_copy("empty", tmp_path)
    before, profile, _ = scan(workdir)

    assert profile["mode"] == "empty"
    assert profile["projects"] == []
    assert git_status(workdir) == before
