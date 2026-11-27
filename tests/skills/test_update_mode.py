"""Update mode: cook snapshot, plan carry-over, build skipping."""
import json
import shutil

from conftest import REPO, run_script


def read(rel):
    return (REPO / rel).read_text()


def test_cook_describes_snapshot_and_full():
    cook = read("skills/cook/SKILL.md")
    for needle in (".sauces/previous/", "design_diff.py", "--full", "design-diff.json", "update-mode.md"):
        assert needle in cook, needle
    assert "--full" in cook.split("---")[1]  # argument-hint in the frontmatter


def test_update_mode_reference_covers_rules():
    text = read("skills/plan/references/update-mode.md")
    for needle in ("unchanged", "affects", "extend", "never delete", "re-verif", "strings[]",
                   "TODO(sauces)", "Removed", "--full"):
        assert needle in text, needle
    assert "update-mode.md" in read("skills/plan/SKILL.md")
    assert "update-mode.md" in read("skills/build/SKILL.md")


def test_plan_schema_accepts_update_fields(tmp_path):
    plan = json.loads((REPO / "tests/data/sauces_sample/plan.json").read_text())
    plan["update"] = {"from_plan": ".sauces/previous/plan.json", "changed": ["login--default"],
                      "added": [], "removed": [], "unchanged": ["login--error", "login--loading"]}
    plan["items"][0]["update"] = "unchanged"
    plan["items"][0]["affects"] = ["login--error"]
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    schema = REPO / "skills/plan/references/plan-schema.json"
    assert run_script("check_json.py", str(schema), str(path)).returncode == 0
    plan["items"][0]["update"] = "stale"
    path.write_text(json.dumps(plan))
    assert run_script("check_json.py", str(schema), str(path)).returncode == 1


def test_report_shows_what_changed(tmp_path):
    d = tmp_path / "s"
    shutil.copytree(REPO / "tests/data/sauces_sample", d)
    (d / "design-diff.json").write_text(json.dumps({
        "states": [
            {"id": "login--default", "status": "changed", "reason": "3.05% pixel difference"},
            {"id": "login--error", "status": "unchanged", "reason": "0.00% pixel difference"},
            {"id": "login--old", "status": "removed", "reason": "state is not in the new design"}],
        "tokens": {k: {"added": [], "removed": [], "changed": []} for k in ("colors", "typography", "spacing", "radii")},
        "copy": {"added": [], "removed": [], "changed": [{"state": "login--default", "old": "Sign in", "new": "Log in"}]},
        "assets": {"added": [], "removed": [], "changed": []},
        "summary": {"changed": 1, "added": 0, "removed": 1, "unchanged": 1}}))
    out = tmp_path / "r.html"
    result = run_script("report_render.py", "--sauces-dir", str(d), "-o", str(out))
    assert result.returncode == 0, result.stderr
    html = out.read_text()
    assert 'id="changes"' in html and "What changed" in html
    assert "3.05% pixel difference" in html
    assert "Sign in" in html and "Log in" in html
    assert "re-verified" in html


def test_report_without_diff_has_no_changes_section(tmp_path):
    out = tmp_path / "r.html"
    assert run_script("report_render.py", "--sauces-dir", str(REPO / "tests/data/sauces_sample"),
                      "-o", str(out)).returncode == 0
    assert 'id="changes"' not in out.read_text()
