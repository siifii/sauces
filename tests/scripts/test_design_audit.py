import importlib.util
import json

import pytest

from conftest import REPO, run_script


def _load():
    spec = importlib.util.spec_from_file_location("design_audit", REPO / "scripts" / "design_audit.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


da = _load()


def _state(name, layout=None):
    s = {"id": name, "name": name, "reference": f".sauces/references/login--{name}.png", "source": 0}
    if layout is not None:
        s["layout"] = layout
    return s


def _login_layout(button_height=52, gap=16, caption_size=12, label_color="#1B1B1F"):
    return {
        "type": "column", "confidence": 0.9, "assumed_dpr": 2, "size": [390, 844],
        "style": {"background": "#FFFFFF", "padding": [96, 24, 0, 24], "gap": gap},
        "children": [
            {"type": "text", "text": "Welcome back", "confidence": 0.95,
             "style": {"color": "#1B1B1F", "size": 28, "weight": 600}},
            {"type": "component", "component": {"kind": "text-field", "variant": "outlined"},
             "text": "Email", "confidence": 0.9,
             "style": {"height": 56, "width": "fill", "radius": 12,
                       "border": {"width": 1, "color": "#79747E"}},
             "children": [{"type": "text", "text": "Email", "confidence": 0.9,
                           "style": {"color": label_color, "size": caption_size, "weight": 400,
                                     "background": "#FFFFFF"}}]},
            {"type": "component", "component": {"kind": "button", "variant": "filled"},
             "text": "Sign in", "confidence": 0.9,
             "style": {"height": button_height, "width": "fill", "radius": 12,
                       "background": "#3D5AFE", "color": "#FFFFFF", "size": 16, "weight": 600}},
        ],
    }


def _manifest(states=None, colors=None):
    return {
        "version": 1,
        "sources": [{"ref": "login.png", "kind": "image", "status": "ok"}],
        "screens": [{"id": "login", "name": "Login",
                     "states": states if states is not None else [_state("default", _login_layout())]}],
        "tokens": {"colors": colors or [{"hex": "#3D5AFE", "origin": "extracted"},
                                        {"hex": "#FFFFFF", "name": "surface", "origin": "extracted"}],
                   "typography": [], "spacing": [16, 24], "radii": [12]},
        "assets": [],
    }


def test_contrast_black_white_is_21():
    assert da.contrast_ratio("#000000", "#FFFFFF") == pytest.approx(21.0, abs=0.01)
    assert da.contrast_ratio("#FFFFFF", "#000000") == pytest.approx(21.0, abs=0.01)


def test_contrast_aa_failure():
    r = da.contrast_ratio("#777777", "#FFFFFF")
    assert r < 4.5
    assert r == pytest.approx(4.48, abs=0.01)


def test_delta_e76():
    assert da.delta_e76("#3D5AFE", "#3D5AFE") == 0
    assert da.delta_e76("#000000", "#FFFFFF") == pytest.approx(100.0, abs=0.01)


def test_near_duplicates():
    pairs = da.near_duplicate_colors(["#3D5AFE", "#3E5BFE", "#B3261E"])
    assert [(a, b) for a, b, _ in pairs] == [("#3D5AFE", "#3E5BFE")]
    assert pairs[0][2] < 3.0
    assert da.near_duplicate_colors(["#3D5AFE", "#B3261E"]) == []
    assert da.near_duplicate_colors(["#3d5afe", "#3D5AFE"]) == []  # same color, not a pair


def test_spacing_outliers():
    assert da.spacing_outliers([4, 8, 13, 16]) == [13]
    assert da.spacing_outliers([0, 2, 8, 24.5]) == []  # 0 and hairline 2 allowed, 0.5 px tolerance
    assert da.spacing_outliers([6, 12], grid=8) == [6, 12]


def test_missing_states():
    m = _manifest()
    assert da.missing_states(m) == {"login": ["loading", "error"]}
    m["screens"][0]["states"] += [_state("loading", _login_layout()), _state("error", _login_layout())]
    assert da.missing_states(m) == {}


def test_missing_states_lists_and_plain_screens():
    list_layout = {"type": "column", "confidence": 1, "children": [
        {"type": "component", "component": {"kind": "list-item", "variant": "default"},
         "text": "Row", "confidence": 1}]}
    plain = {"type": "column", "confidence": 1, "children": [
        {"type": "text", "text": "About", "confidence": 1}]}
    m = _manifest()
    m["screens"] = [
        {"id": "inbox", "name": "Inbox", "states": [_state("default", list_layout)]},
        {"id": "about", "name": "About", "states": [_state("default", plain), _state("dark", plain)]},
    ]
    assert da.missing_states(m) == {"inbox": ["loading", "empty"]}


def test_small_touch_target():
    m = _manifest(states=[_state("default", _login_layout(button_height=36))])
    hits = da.small_touch_targets(m)
    assert len(hits) == 1, hits
    assert hits[0]["kind"] == "button" and hits[0]["height"] == 36
    assert hits[0]["screen"] == "login" and hits[0]["state"] == "default"
    assert da.small_touch_targets(_manifest()) == []


def test_small_text():
    m = _manifest(states=[_state("default", _login_layout(caption_size=11))])
    hits = da.small_text(m)
    assert [h["text"] for h in hits] == ["Email"] and hits[0]["size"] == 11
    assert da.small_text(_manifest()) == []


def test_audit_cli_writes_findings(tmp_path):
    layout = _login_layout(button_height=36, gap=14, caption_size=11, label_color="#999999")
    m = _manifest(states=[_state("default", layout)],
                  colors=[{"hex": "#3D5AFE", "origin": "extracted"},
                          {"hex": "#3E5BFE", "origin": "extracted"},
                          {"hex": "#FFFFFF", "name": "surface", "origin": "extracted"}])
    sauces = tmp_path / ".sauces"
    sauces.mkdir()
    (sauces / "manifest.json").write_text(json.dumps(m))
    r = run_script("design_audit.py", "--manifest", str(sauces / "manifest.json"))
    assert r.returncode == 0, r.stderr
    out = json.loads((sauces / "design-audit.json").read_text())
    assert out["version"] == 1
    findings = out["findings"]
    cats = {f["category"] for f in findings}
    assert {"accessibility", "consistency", "states"} <= cats, findings
    for f in findings:
        assert f["id"].startswith(f"audit-{f['category']}-")
        assert f["severity"] in ("high", "medium", "low")
        assert f["screen"] and f["detail"] and f["guideline"]
        assert isinstance(f["measured"], dict) and f["measured"]
    assert len({f["id"] for f in findings}) == len(findings)
    contrast = [f for f in findings if "contrast_ratio" in f["measured"]]
    assert contrast and contrast[0]["measured"]["background"] == "#FFFFFF", contrast
    assert any(f["measured"].get("height") == 36 for f in findings)
    assert any(f["measured"].get("value") == 14 for f in findings)
    assert any(f["measured"].get("delta_e") is not None for f in findings)
    assert any(f["measured"].get("missing") == ["loading", "error"] for f in findings)
    order = ["high", "medium", "low"]
    assert [order.index(f["severity"]) for f in findings] == sorted(order.index(f["severity"]) for f in findings)


def test_audit_cli_output_flag_and_bad_manifest(tmp_path):
    good = tmp_path / "m.json"
    good.write_text(json.dumps(_manifest()))
    out = tmp_path / "audit.json"
    r = run_script("design_audit.py", "--manifest", str(good), "-o", str(out))
    assert r.returncode == 0, r.stderr
    assert json.loads(out.read_text())["version"] == 1
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert run_script("design_audit.py", "--manifest", str(bad)).returncode == 2
    assert run_script("design_audit.py", "--manifest", str(tmp_path / "missing.json")).returncode == 2
    bad.write_text(json.dumps({"version": 1}))
    assert run_script("design_audit.py", "--manifest", str(bad)).returncode == 2
