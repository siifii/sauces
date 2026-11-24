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


def _screen(layout, states=("default",)):
    return _manifest(states=[_state(s, layout) for s in states])


def _col(*children, kind="column", **style):
    return {"type": kind, "confidence": 1, "style": {"background": "#FFFFFF", **style},
            "children": list(children)}


def _text(text, **style):
    return {"type": "text", "text": text, "confidence": 1, "style": style}


def _comp(kind, variant="default", text=None, children=None, **style):
    n = {"type": "component", "component": {"kind": kind, "variant": variant},
         "confidence": 1, "style": style}
    if text:
        n["text"] = text
    if children:
        n["children"] = children
    return n


def test_large_text_threshold():
    # #949494 on white is about 3.03:1: passes as large text, fails as normal text
    grey = "#949494"
    assert 3.0 <= da.contrast_ratio(grey, "#FFFFFF") < 4.5
    cases = [(24, 400, False), (23, 400, True), (18.66, 700, False), (18.66, 600, True)]
    for size, weight, flagged in cases:
        hits = da.text_contrast(_screen(_col(_text("T", color=grey, size=size, weight=weight))))
        assert bool(hits) is flagged, (size, weight, hits)


def test_alpha_text_is_composited():
    assert da.contrast_ratio("#00000080", "#FFFFFF") == pytest.approx(
        da.contrast_ratio("#7F7F7F", "#FFFFFF"), abs=0.01)
    assert da.composite("#00000080", "#FFFFFF") == "#7F7F7F"
    hits = da.text_contrast(_screen(_col(_text("Hint", color="#0000004D", size=16))))
    assert hits and hits[0]["contrast_ratio"] < 3, hits
    # translucent background over a dark parent
    layout = _col(_col(_text("On scrim", color="#FFFFFF", size=16), background="#FFFFFF33"),
                  background="#000000")
    assert da.text_contrast(_screen(layout)) == []


def test_text_color_inherited_from_ancestor():
    layout = _col(_col(_text("Muted", size=16), color="#AAAAAA", background="#FFFFFF"))
    hits = da.text_contrast(_screen(layout))
    assert [h["color"] for h in hits] == ["#AAAAAA"], hits
    assert da.text_contrast(_screen(_col(_text("No color", size=16)))) == []


def test_disabled_text_exempt():
    btn = _comp("button", "disabled", "Sign in", height=52, background="#E0E0E0",
                color="#BDBDBD", size=16)
    assert da.text_contrast(_screen(_col(btn))) == []
    btn["component"]["variant"] = "filled"
    assert da.text_contrast(_screen(_col(btn)))


def test_border_contrast():
    field = _comp("text-field", "outlined", "Email", height=56,
                  border={"width": 1, "color": "#DDDDDD"})
    hits = da.border_contrast(_screen(_col(field)))
    assert hits and hits[0]["contrast_ratio"] < 3 and hits[0]["background"] == "#FFFFFF", hits
    field["style"]["border"]["color"] = "#79747E"
    assert da.border_contrast(_screen(_col(field))) == []


def test_link_line_height_fallback():
    link = _comp("link", "text", "Forgot password?", line_height=20, color="#3D5AFE", size=14)
    hits = da.small_touch_targets(_screen(_col(link)))
    assert hits and hits[0]["height"] == 20 and hits[0]["measured_from"] == "line_height", hits


def test_text_field_icon_is_a_target():
    eye = {"type": "component", "component": {"kind": "icon", "variant": "default"},
           "description": "eye (show password)", "confidence": 1,
           "style": {"width": 24, "height": 24}}
    field = _comp("text-field", "outlined", "Password", children=[eye], height=56)
    hits = da.small_touch_targets(_screen(_col(field)))
    assert [h["kind"] for h in hits] == ["icon"], hits
    lone_icon = dict(eye)
    assert da.small_touch_targets(_screen(_col(lone_icon))) == []  # decorative icon


def test_touch_target_severity_uses_wcag_spacing():
    def run(gap):
        row = _col(_comp("icon-button", text="A", width=20, height=20),
                   _comp("icon-button", text="B", width=20, height=20), kind="row", gap=gap)
        findings, _ = da.audit(_screen(row))
        return [f for f in findings if f["measured"].get("kind") == "icon-button"]

    close = run(0)
    assert close and all(f["severity"] == "high" for f in close), close
    assert close[0]["measured"]["wcag_spacing"] == "fails"
    spaced = run(8)
    assert spaced and all(f["severity"] == "medium" for f in spaced), spaced
    assert spaced[0]["measured"]["wcag_spacing"] == "passes"
    link = _comp("link", "text", "Forgot password?", line_height=20)
    findings, _ = da.audit(_screen(_col(link)))
    assert [f["severity"] for f in findings if f["measured"].get("kind") == "link"] == ["medium"]


def test_pill_radius_exempt():
    pill = _comp("button", "filled", "Go", height=52, radius=26, background="#3D5AFE",
                 color="#FFFFFF", size=16)
    m = _screen(_col(pill))
    m["tokens"]["radii"] = []
    findings, _ = da.audit(m)
    assert not [f for f in findings if f["measured"].get("value") == 26], findings
    pill["style"]["height"] = 80  # radius 26 on an 80 px box is a corner, off-grid
    findings, _ = da.audit(_screen(_col(pill)))
    assert [f for f in findings if f["measured"].get("value") == 26]


def test_mixed_radii():
    cards = [_comp("card", radius=r, height=100) for r in (4, 8, 12)]
    m = _screen(_col(*cards))
    m["tokens"]["radii"] = []
    assert da.mixed_radii(m) is None
    cards.append(_comp("card", radius=20, height=100))
    cards.append(_comp("chip", radius=16, height=32))  # pill: excluded
    r = da.mixed_radii(_screen(_col(*cards)))
    assert r == {"radii": [4, 8, 12, 20], "count": 4, "maximum": 3}, r
    findings, _ = da.audit(_screen(_col(*cards)))
    assert any(f["measured"].get("radii") == [4, 8, 12, 20] for f in findings)


def test_type_sprawl():
    ok = _col(*[_text(str(s), size=s, color="#000000") for s in (28, 16, 14, 12)])
    assert da.type_sprawl(_screen(ok)) == {}
    many = _col(*[_text(str(s), size=s, weight=w, color="#000000")
                  for s, w in ((28, 600), (22, 400), (16, 400), (16, 600), (14, 500),
                               (12, 400), (11, 500))])
    out = da.type_sprawl(_screen(many))
    assert out["login"]["count"] == 7 and out["login"]["off_scale_sizes"] == [], out
    off = _col(*[_text(str(s), size=s, color="#000000") for s in (18, 19, 16)])
    assert da.type_sprawl(_screen(off))["login"]["off_scale_sizes"] == [18, 19]


def test_grid_finding_also_in():
    m = _screen(_login_layout(gap=14), states=("default", "error"))
    findings, _ = da.audit(m)
    grid = [f for f in findings if f["measured"].get("value") == 14]
    assert len(grid) == 1, grid
    assert grid[0]["state"] == "default" and grid[0]["also_in"] == ["login/error"], grid


def test_merged_findings_list_screen_state():
    m = _screen(_login_layout(button_height=36), states=("default", "loading"))
    findings, _ = da.audit(m)
    btn = [f for f in findings if f["measured"].get("height") == 36]
    assert len(btn) == 1 and btn[0]["also_in"] == ["login/loading"], btn


def test_category_sort_order():
    assert da.CATEGORIES == ["accessibility", "ux", "states", "localization", "platform",
                             "consistency"]
