"""Update mode: cook snapshot, plan carry-over, build skipping."""
import json

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
