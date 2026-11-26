"""Web platforms (web-react, web-html): schemas, references, fixtures and wiring."""

import copy
import json

import pytest

from conftest import REPO, run_script

WEB = ["web-react", "web-html"]
SAMPLE = REPO / "tests/data/sauces_sample"
MANIFEST_SCHEMA = "skills/ingest/references/manifest-schema.json"
PLAN_SCHEMA = "skills/plan/references/plan-schema.json"


def check(schema, data, tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps(data))
    return run_script("check_json.py", str(REPO / schema), str(path))


@pytest.mark.parametrize("platform", WEB)
def test_web_platform_in_enums(platform):
    for skill, schema in (
        ("scan-project", "profile-schema.json"),
        ("plan", "plan-schema.json"),
        ("verify", "summary-schema.json"),
    ):
        properties = json.loads((REPO / "skills" / skill / "references" / schema).read_text())["properties"]
        if skill == "scan-project":
            properties = properties["projects"]["items"]["properties"]
        assert platform in properties["platform"]["enum"], (skill, platform)


def test_platform_order_in_enums():
    order = ["flutter", "ios-swiftui", "android-compose", "kmp-cmp", "react-native",
             "web-react", "web-html"]
    for skill, schema in (("plan", "plan-schema.json"), ("verify", "summary-schema.json"),
                          ("scan-project", "profile-schema.json")):
        properties = json.loads((REPO / "skills" / skill / "references" / schema).read_text())["properties"]
        if skill == "scan-project":
            properties = properties["projects"]["items"]["properties"]
        assert properties["platform"]["enum"] == order, skill


def test_manifest_accepts_breakpoint_screens(tmp_path):
    manifest = json.loads((SAMPLE / "manifest.json").read_text())
    r = check(MANIFEST_SCHEMA, manifest, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    web = copy.deepcopy(manifest)
    web["sources"][0]["viewport"] = {"width": 1440, "dpr": 1}
    screen = web["screens"][0]
    screen.update({"id": "login@1440", "base": "login", "breakpoint": 1440})
    r = check(MANIFEST_SCHEMA, web, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    web["sources"][0]["viewport"] = {"width": "wide", "dpr": 1}
    assert check(MANIFEST_SCHEMA, web, tmp_path).returncode == 1


def test_web_plan_requires_breakpoints(tmp_path):
    plan = json.loads((SAMPLE / "plan.json").read_text())
    assert check(PLAN_SCHEMA, plan, tmp_path).returncode == 0
    web = dict(plan, platform="web-react")
    r = check(PLAN_SCHEMA, web, tmp_path)
    assert r.returncode == 1 and "breakpoints" in r.stdout, r.stdout + r.stderr
    web["breakpoints"] = [{"name": "desktop", "min_width": 1024, "source": "design"}]
    r = check(PLAN_SCHEMA, web, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    web["breakpoints"][0]["source"] = "guess"
    assert check(PLAN_SCHEMA, web, tmp_path).returncode == 1


def test_ingest_breakpoint_reference():
    text = (REPO / "skills/ingest/references/breakpoints.md").read_text()
    for needle in ("viewport", "@", "narrowest", "web-react", "web-html", "not duplicates"):
        assert needle in text
    assert "references/breakpoints.md" in (REPO / "skills/ingest/SKILL.md").read_text()


def test_plan_skill_lists_web_and_breakpoints():
    text = (REPO / "skills/plan/SKILL.md").read_text()
    assert "web-react" in text and "web-html" in text and "breakpoints" in text
