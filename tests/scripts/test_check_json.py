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


def test_nested_unsupported_keyword_is_error_even_on_empty_data(tmp_path):
    for schema in ({"properties": {"a": {"oneOf": []}}},
                   {"properties": {"a": {"items": {"anyOf": []}}}},
                   {"items": {"allOf": []}}):
        r = check(tmp_path, schema, {})
        assert r.returncode == 2, schema
        assert "unsupported keyword" in r.stderr


@pytest.mark.parametrize("schema", [
    {"properties": {"a": {"pattern": "("}}},
    {"properties": []},
    {"enum": "x"},
    {"required": "a"},
    {"type": "strng"},
    {"additionalProperties": {"type": "string"}},
])
def test_malformed_schema_exits_2(tmp_path, schema):
    r = check(tmp_path, schema, {})
    assert r.returncode == 2
    assert "Traceback" not in r.stderr and r.stderr.strip()


@pytest.mark.parametrize("rel", SCHEMAS)
def test_shipped_schemas_use_supported_keywords(tmp_path, rel):
    r = check(tmp_path, (REPO / rel).read_text(), {})
    assert r.returncode == 1, r.stderr  # data {} is invalid, schema itself is fine
    assert "unsupported" not in r.stderr


def test_shipped_schema_check_catches_nested_keyword(tmp_path):
    schema = json.loads((REPO / SCHEMAS[0]).read_text())
    schema["properties"]["screens"]["items"]["properties"]["states"]["items"]["oneOf"] = []
    assert check(tmp_path, schema, {}).returncode == 2


def _schema(rel):
    return json.loads((REPO / rel).read_text())


def test_profile_schema(tmp_path):
    proj = {
        "root": ".", "platform": "flutter", "architecture": "bloc", "state_management": "bloc",
        "theme": {"location": "lib/theme.dart", "tokens_source": "ThemeData"},
        "localization": {"system": "arb", "rtl": False, "locales": ["en"]},
        "components": [{"name": "Btn", "path": "lib/btn.dart", "params": ["label"], "has_preview": False}],
        "conventions": {"feature_folders": "feature-first", "naming": "snake_case"},
        "screenshot_tooling": {"present": False},
        "findings": [{"id": "f1", "area": "colors", "detail": "hard-coded", "paths": ["a.dart"]}],
    }
    data = {"version": 1, "mode": "existing", "projects": [proj]}
    assert check(tmp_path, _schema(SCHEMAS[1]), data).returncode == 0
    proj["platform"] = "windows"
    r = check(tmp_path, _schema(SCHEMAS[1]), data)
    assert r.returncode == 1 and "projects[0].platform" in r.stdout


def _plan(**over):
    p = {"version": 1, "approved": False, "approved_by": None, "platform": "flutter",
         "items": [{"id": "i1", "design_ref": "login", "decision": "new", "name": "LoginForm",
                    "path": "lib/login.dart", "level": "organism", "confidence": 0.8}],
         "recommendations": [], "strings": [], "dependency_changes": []}
    p.update(over)
    return p


def test_plan_schema(tmp_path):
    assert check(tmp_path, _schema(SCHEMAS[2]), _plan(approved=True, approved_by="user")).returncode == 0
    bad = _plan()
    bad["items"][0]["decision"] = "maybe"
    r = check(tmp_path, _schema(SCHEMAS[2]), bad)
    assert r.returncode == 1 and "items[0].decision" in r.stdout


def test_state_schema(tmp_path):
    stage = {"status": "pending", "finished_at": None, "inputs_hash": None}
    names = ["ingest", "scan", "plan", "build", "verify", "report"]
    data = {"version": 1, "stages": {n: dict(stage) for n in names},
            "generated_files": [], "changed_files": []}
    assert check(tmp_path, _schema(SCHEMAS[3]), data).returncode == 0
    data["stages"]["scan"]["status"] = "running"
    r = check(tmp_path, _schema(SCHEMAS[3]), data)
    assert r.returncode == 1 and "stages.scan.status" in r.stdout


def test_manifest_design_system_optional(tmp_path):
    schema = load_schema()
    ds = {
        "signals": [
            {"kind": "figma-naming", "detail": "pages named Atoms/Molecules", "evidence": "Atoms/Button"},
            {"kind": "repetition", "detail": "text-field appears 6 times across 3 states"},
        ],
        "component_candidates": [
            {"name": "text-field", "occurrences": 6, "screens": ["login"], "variants": ["outlined", "error"]},
        ],
    }
    assert check(tmp_path, schema, manifest(design_system=ds)).returncode == 0
    ds["signals"][0]["kind"] = "vibes"
    r = check(tmp_path, schema, manifest(design_system=ds))
    assert r.returncode == 1 and "design_system.signals[0].kind" in r.stdout
    del ds["component_candidates"][0]["occurrences"]
    ds["signals"][0]["kind"] = "library"
    r = check(tmp_path, schema, manifest(design_system=ds))
    assert r.returncode == 1 and "design_system.component_candidates[0]" in r.stdout


def test_profile_component_structure(tmp_path):
    proj = {
        "root": ".", "platform": "flutter", "architecture": "feature-first-bloc",
        "state_management": "bloc",
        "theme": {"location": "lib/core/theme/app_theme.dart", "tokens_source": "none"},
        "localization": {"system": "arb", "rtl": False, "locales": ["en"]},
        "components": [], "conventions": {"feature_folders": "x", "naming": "y"},
        "screenshot_tooling": {"present": False}, "findings": [],
        "component_structure": {"pattern": "feature-first",
                                "paths": ["lib/core/widgets", "lib/features"],
                                "evidence": ["shared widgets in lib/core/widgets"]},
    }
    data = {"version": 1, "mode": "existing", "projects": [proj]}
    assert check(tmp_path, _schema(SCHEMAS[1]), data).returncode == 0
    proj["component_structure"]["pattern"] = "follow"
    r = check(tmp_path, _schema(SCHEMAS[1]), data)
    assert r.returncode == 1 and "projects[0].component_structure.pattern" in r.stdout


def _structure(**over):
    s = {"recommended": "follow", "choice": "follow",
         "reasons": ["the project already has a shared core", "one screen"],
         "options": [{"id": "follow", "label": "Follow the project",
                      "folders": ["lib/core/widgets", "lib/features/<f>/view"]},
                     {"id": "atomic", "label": "Atomic Design",
                      "folders": ["lib/design_system/atoms"]}]}
    s.update(over)
    return s


def test_plan_structure_and_layer(tmp_path):
    plan = _plan(structure=_structure())
    plan["items"][0]["layer"] = "organisms"
    assert check(tmp_path, _schema(SCHEMAS[2]), plan).returncode == 0
    assert check(tmp_path, _schema(SCHEMAS[2]), _plan()).returncode == 0  # structure stays optional
    r = check(tmp_path, _schema(SCHEMAS[2]), _plan(structure=_structure(recommended="custom")))
    assert r.returncode == 1 and "structure.recommended" in r.stdout
    bad = _plan()
    bad["items"][0]["layer"] = 3
    r = check(tmp_path, _schema(SCHEMAS[2]), bad)
    assert r.returncode == 1 and "items[0].layer" in r.stdout
