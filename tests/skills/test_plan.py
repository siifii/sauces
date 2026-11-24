"""Headless tests for the plan skill (marker: skill).

One module-scoped pipeline run (scan-project + ingest + plan in one flutter-bloc copy)
feeds every assertion, so scan and ingest are paid for once.
"""
import json
import re
import shutil
import subprocess

import pytest

from conftest import REPO, fixture_copy, needs_claude, run_script, run_skill

SCHEMA = REPO / "skills" / "plan" / "references" / "plan-schema.json"
LOGIN = REPO / "examples" / "designs" / "login"
COPY = {
    "Welcome back", "Email", "Password", "Sign in", "Forgot password?",
    "Incorrect email or password",
}
PLAN_MD_SECTIONS = (
    "Design-system structure", "Summary", "Components", "Tokens", "Strings",
    "Recommendations", "Dependency changes",
)

pytestmark = [pytest.mark.skill, needs_claude]


def git_status(workdir):
    """Porcelain status lines, ignoring Sauces' own .sauces/ working folder."""
    out = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=workdir, capture_output=True, text=True, check=True,
    ).stdout
    return [line for line in out.splitlines() if not line[3:].startswith(".sauces/")]


def copy_design(dest):
    """The login PNGs, the eye icon and description.md (no PDF, so no pdftoppm needed)."""
    (dest / "icons").mkdir(parents=True)
    for state in ("default", "error", "loading"):
        shutil.copy(LOGIN / f"login--{state}.png", dest / f"login--{state}.png")
    shutil.copy(LOGIN / "icons" / "eye.svg", dest / "icons" / "eye.svg")
    shutil.copy(LOGIN / "description.md", dest / "description.md")
    return dest


@pytest.fixture(scope="module")
def pipeline(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("plan")
    workdir = fixture_copy("flutter-bloc", tmp)
    design = copy_design(tmp / "design")
    before = git_status(workdir)
    logs = []
    for prompt in ("/sauces:scan-project", f'/sauces:ingest "{design}"', "/sauces:plan"):
        result = run_skill(workdir, prompt)
        logs.append(f"$ {prompt}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    plan_path = workdir / ".sauces" / "plan.json"
    assert plan_path.is_file(), "no plan written\n" + "\n".join(logs)
    check = run_script("check_json.py", str(SCHEMA), str(plan_path))
    assert check.returncode == 0, check.stdout + check.stderr
    profile = json.loads((workdir / ".sauces" / "project-profile.json").read_text())
    return {
        "workdir": workdir,
        "before": before,
        "plan": json.loads(plan_path.read_text()),
        "profile": profile,
        "plan_md": (workdir / ".sauces" / "plan.md").read_text(),
        "output": logs[-1],
    }


def test_plan_reuses_existing(pipeline):
    items = pipeline["plan"]["items"]
    for suffix in ("app_button.dart", "app_text_field.dart"):
        matched = [i for i in items if (i.get("existing_path") or "").endswith(suffix)]
        assert matched, (suffix, items)
        assert all(i["decision"] in ("reuse", "extend") for i in matched), matched
    new_controls = [
        i for i in items
        if i["decision"] == "new" and re.search(r"button|field", i["name"].lower())
    ]
    assert not new_controls, new_controls


def test_plan_recommendation_for_card_color(pipeline):
    project = pipeline["profile"]["projects"][0]
    color_ids = {
        f["id"] for f in project["findings"]
        if f["area"] == "colors" and "lib/core/widgets/app_card.dart" in f["paths"]
    }
    assert color_ids, project["findings"]
    recs = [r for r in pipeline["plan"]["recommendations"] if r["finding_id"] in color_ids]
    assert recs, pipeline["plan"]["recommendations"]
    for rec in recs:
        assert "keep" in {o["id"] for o in rec["options"]}, rec
        assert rec["choice"] == "keep", rec


def test_plan_strings_cover_copy(pipeline):
    values = {s["value"] for s in pipeline["plan"]["strings"]}
    assert COPY <= values, values


def test_plan_eval_approved(pipeline):
    plan = pipeline["plan"]
    assert plan["approved"] is True, plan
    assert plan["approved_by"] == "eval", plan
    assert all(r["choice"] == "keep" for r in plan["recommendations"]), plan["recommendations"]


def test_plan_structure(pipeline):
    plan = pipeline["plan"]
    structure = plan.get("structure") or {}
    assert structure.get("recommended") == "follow", structure
    assert structure.get("choice") == structure["recommended"], structure
    assert len(structure.get("reasons", [])) >= 2, structure
    assert all((i.get("layer") or "").strip() for i in plan["items"]), plan["items"]


def test_plan_md_sections(pipeline):
    md = pipeline["plan_md"]
    headings = [line.lstrip("#").strip() for line in md.splitlines() if line.startswith("#")]
    for section in PLAN_MD_SECTIONS:
        assert any(h.startswith(section) for h in headings), (section, headings)
    assert "```mermaid" in md and "graph LR" in md, md


def test_plan_does_not_touch_code(pipeline):
    assert git_status(pipeline["workdir"]) == pipeline["before"]
