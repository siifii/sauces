import json

import pytest

from conftest import REPO, run_script

MANIFEST_SCHEMA = REPO / "skills" / "ingest" / "references" / "manifest-schema.json"
SCHEMAS = [
    "skills/ingest/references/manifest-schema.json",
    "skills/scan-project/references/profile-schema.json",
    "skills/plan/references/plan-schema.json",
    "skills/cook/references/state-schema.json",
]


def manifest(**over):
    m = {
        "version": 1,
        "sources": [{"ref": "login.png", "kind": "image", "status": "ok"}],
        "screens": [{
            "id": "login", "name": "Login",
            "states": [{"id": "default", "name": "default",
                        "reference": ".sauces/references/login--default.png", "source": 0}],
        }],
        "tokens": {"colors": [{"hex": "#3D5AFE", "origin": "extracted"}],
                   "typography": [], "spacing": [8], "radii": [4]},
        "assets": [],
    }
    m.update(over)
    return m


def check(tmp_path, schema, data):
    s = tmp_path / "schema.json"
    d = tmp_path / "data.json"
    s.write_text(json.dumps(schema) if not isinstance(schema, str) else schema)
    d.write_text(json.dumps(data))
    return run_script("check_json.py", str(s), str(d))


def load_schema():
    return json.loads(MANIFEST_SCHEMA.read_text())


def test_valid_manifest_passes(tmp_path):
    r = check(tmp_path, load_schema(), manifest())
    assert r.returncode == 0, r.stdout + r.stderr


def test_missing_required_reports_path(tmp_path):
    m = manifest()
    del m["screens"][0]["states"][0]["reference"]
    r = check(tmp_path, load_schema(), m)
    assert r.returncode == 1
    assert "screens[0].states[0]: missing required 'reference'" in r.stdout


def test_enum_violation(tmp_path):
    r = check(tmp_path, {"type": "object", "properties": {"decision": {"enum": ["reuse", "new"]}}},
              {"decision": "maybe"})
    assert r.returncode == 1
    assert "decision:" in r.stdout


def test_unknown_keyword_is_error(tmp_path):
    r = check(tmp_path, {"oneOf": []}, {})
    assert r.returncode == 2
    assert "unsupported keyword: oneOf" in r.stderr


def test_type_rules(tmp_path):
    schema = {"type": "object", "properties": {
        "i": {"type": "integer"}, "n": {"type": "number"},
        "nul": {"type": ["string", "null"]}}}
    assert check(tmp_path, schema, {"i": 2.0, "n": 1.5, "nul": None}).returncode == 0
    r = check(tmp_path, schema, {"i": True, "n": True})
    assert r.returncode == 1
    assert "i:" in r.stdout and "n:" in r.stdout


def test_pattern_min_max_additional(tmp_path):
    schema = {"type": "object", "additionalProperties": False,
              "properties": {"h": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"},
                             "c": {"type": "number", "minimum": 0, "maximum": 1}}}
    r = check(tmp_path, schema, {"h": "red", "c": 2, "extra": 1})
    assert r.returncode == 1
    assert "h:" in r.stdout and "c:" in r.stdout and "unexpected property 'extra'" in r.stdout


def test_root_error_path_and_nullable_enum(tmp_path):
    r = check(tmp_path, {"type": "object"}, [])
    assert r.returncode == 1 and r.stdout.startswith("$:")
    schema = {"type": ["string", "null"], "enum": ["user", "eval", None]}
    assert check(tmp_path, schema, None).returncode == 0


def test_unreadable_inputs(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{nope")
    ok = tmp_path / "ok.json"
    ok.write_text("{}")
    assert run_script("check_json.py", str(ok), str(bad)).returncode == 2
    assert run_script("check_json.py", str(tmp_path / "missing.json"), str(ok)).returncode == 2


@pytest.mark.parametrize("rel", SCHEMAS)
def test_shipped_schemas_use_supported_keywords(tmp_path, rel):
    r = check(tmp_path, (REPO / rel).read_text(), {})
    assert r.returncode in (0, 1), r.stderr  # not 2: no unsupported keywords
    assert "unsupported" not in r.stderr
