import json
import os
import re
import shutil

import pytest

from conftest import REPO, run_script

SAMPLE = REPO / "tests" / "data" / "sauces_sample"
SECTIONS = ("summary", "fidelity", "design-system", "graph", "localization", "audit", "files", "todos",
            "practices", "recommendations")


def render(sauces_dir, tmp_path):
    out = tmp_path / "report.html"
    result = run_script("report_render.py", "--sauces-dir", str(sauces_dir), "-o", str(out))
    assert result.returncode == 0, result.stdout + result.stderr
    return out.read_text()


def section(html, sid):
    m = re.search(rf'<section[^>]*\bid="{sid}"[^>]*>(.*?)</section>', html, re.S)
    assert m, sid
    return m.group(1)


@pytest.fixture(scope="module")
def sample_html(tmp_path_factory):
    return render(SAMPLE, tmp_path_factory.mktemp("report"))


def test_render_sections(sample_html):
    for sid in SECTIONS:
        section(sample_html, sid)
    summary = section(sample_html, "summary")
    assert "93.1" in summary  # login--default's final score
    assert "data:image/png;base64," in section(sample_html, "fidelity")


def test_audit_section_lists_suggestions(sample_html):
    audit = section(sample_html, "audit")
    plan = json.loads((SAMPLE / "plan.json").read_text())
    for sug in plan["design_suggestions"]:
        assert sug["title"] in audit, sug["id"]
        assert sug["guideline"] in audit, sug["id"]
    assert re.search(r"Grow the Forgot password\? hit area.*?\bapply\b", audit, re.S)
    assert re.search(r"Merge #3E5BFE into the brand color.*?\bkeep\b", audit, re.S)
    assert "#3E5BFE" in audit and "0.73" in audit  # measured near-duplicate from design-audit.json


def card_value(html, label):
    m = re.search(r'<div class="num">([^<]*)</div><div class="label">' + re.escape(label) + "</div>", html)
    assert m, label
    return m.group(1)


def test_localization_counts(sample_html):
    loc = section(sample_html, "localization")
    assert card_value(loc, "keys added") == "5"
    assert card_value(loc, "keys reused") == "1"
    assert "Forgot password? stays right-aligned" in loc


def test_self_contained(sample_html):
    assert not re.search(r"<link[^>]+rel=[\"']?stylesheet", sample_html, re.I)
    assert "graph LR" in section(sample_html, "graph")  # <pre> text fallback with the source


def test_default_output_makes_no_network_requests(sample_html):
    assert not re.search(r"<script[^>]+\bsrc=", sample_html, re.I)
    assert not re.search(r"""\b(?:src|href)=["']https?://""", sample_html)
    assert "cdn.jsdelivr" not in sample_html
    assert "<svg" in section(sample_html, "graph")  # inline SVG graph, no script needed


def test_graph_svg_is_honest(sample_html):
    graph = section(sample_html, "graph")
    assert "AppTextField (extend, reuse)" in graph  # both decisions, one node
    assert graph.count("AppTextField (") == 2  # the SVG label and the <pre> source (one node each)
    assert "brand" in graph
    assert "-.->" not in graph  # no invented component-to-token edges


def test_allow_cdn_pins_version_with_sri(tmp_path):
    out = tmp_path / "report.html"
    r = run_script("report_render.py", "--sauces-dir", str(SAMPLE), "-o", str(out), "--allow-cdn")
    assert r.returncode == 0, r.stderr
    html = out.read_text()
    tags = re.findall(r"<script[^>]+\bsrc=[^>]*>", html)
    assert len(tags) == 1, tags
    assert re.search(r"mermaid@\d+\.\d+\.\d+/", tags[0]), tags[0]
    assert re.search(r'integrity="sha384-[A-Za-z0-9+/=]+"', tags[0]) and "crossorigin" in tags[0]


def test_files_section_lists_generated_and_changed(sample_html):
    files = section(sample_html, "files")
    assert "lib/features/login/view/login_page.dart" in files
    assert "lib/l10n/app_ar.arb" in files
    assert re.search(r"login_page\.dart</code>.*?new", files, re.S)
    assert re.search(r"app_ar\.arb</code>.*?changed", files, re.S)


def test_files_section_without_state_says_not_run(tmp_path):
    sauces = tmp_path / ".sauces"
    shutil.copytree(SAMPLE, sauces)
    (sauces / "state.json").unlink()
    assert "not run" in section(render(sauces, tmp_path), "files")


def practice_li(html, needle):
    m = re.search(r"<li[^>]*>(?:(?!</li>).)*" + re.escape(needle) + r"(?:(?!</li>).)*</li>",
                  section(html, "practices"), re.S)
    assert m, needle
    return m.group(0)


def test_practice_contradicted_by_rtl_issue_is_not_ticked(sample_html):
    li = practice_li(sample_html, "Directional layout")
    assert "✓" not in li
    assert "Localization" in li  # points at the evidence


def test_practices_without_evidence_say_not_checked(sample_html):
    for needle in ("Colors and type come from the theme", "Existing components are extended"):
        li = practice_li(sample_html, needle)
        assert "not checked" in li and "✓" not in li, needle


def test_practices_ticked_only_with_evidence(tmp_path):
    sauces = tmp_path / ".sauces"
    shutil.copytree(SAMPLE, sauces)
    (sauces / "lint.json").write_text(json.dumps({"version": 1, "findings": []}))
    html = render(sauces, tmp_path)
    assert "✓" in practice_li(html, "Colors and type come from the theme")
    (sauces / "lint.json").write_text(json.dumps({"version": 1, "findings": [
        {"file": "lib/a.dart", "line": 3, "rule": "hardcoded-color", "text": "Colors.red"}]}))
    html = render(sauces, tmp_path)
    li = practice_li(html, "Colors and type come from the theme")
    assert "✓" not in li and "lib/a.dart" in li


def test_rtl_practice_ticked_when_verify_clean(tmp_path):
    sauces = tmp_path / ".sauces"
    shutil.copytree(SAMPLE, sauces)
    summ = json.loads((sauces / "verify" / "summary.json").read_text())
    for r in summ["results"]:
        r["rtl_issues"] = []
    (sauces / "verify" / "summary.json").write_text(json.dumps(summ))
    assert "✓" in practice_li(render(sauces, tmp_path), "Directional layout")


def test_rtl_screenshot_shown(sample_html):
    assert 'alt="RTL"' in section(sample_html, "fidelity")


def test_summary_counts_distinct_components(sample_html):
    summary = section(sample_html, "summary")
    assert card_value(summary, "components reused") == "0"
    assert card_value(summary, "components extended") == "2"  # AppTextField counted once
    assert card_value(summary, "new components") == "1"
    assert card_value(summary, "reuse rate") == "67%"


def test_assets_card_counts_assets_that_landed_in_project(sample_html):
    loc = section(sample_html, "localization")
    assert card_value(loc, "assets created") == "1"
    assert "assets/icons/eye.svg" in loc


def test_missing_inputs(tmp_path):
    sauces = tmp_path / ".sauces"
    sauces.mkdir()
    shutil.copy(SAMPLE / "manifest.json", sauces / "manifest.json")
    html = render(sauces, tmp_path)
    for sid in SECTIONS:
        body = section(html, sid)
        if sid == "summary":
            assert "not run:" not in body and "screens built" in body
        elif sid == "audit":
            assert "not run" in body and "Palette" in body  # palette comes from the manifest
        else:
            assert "not run" in body, sid


def test_unreadable_json_shows_callout(tmp_path):
    sauces = tmp_path / ".sauces"
    shutil.copytree(SAMPLE, sauces)
    (sauces / "todos.json").write_text("{not json")
    html = render(sauces, tmp_path)
    assert "Unreadable inputs" in section(html, "summary") and "todos.json" in section(html, "summary")


@pytest.mark.parametrize("name", ["plan.json", "project-profile.json", "state.json", "verify/summary.json"])
def test_wrong_shape_json_does_not_crash(tmp_path, name):
    sauces = tmp_path / ".sauces"
    shutil.copytree(SAMPLE, sauces)
    (sauces / name).write_text("[1]")
    html = render(sauces, tmp_path)
    assert "Unreadable inputs" in html and name in html


def test_projects_with_non_dict_entries_do_not_crash(tmp_path):
    sauces = tmp_path / ".sauces"
    shutil.copytree(SAMPLE, sauces)
    prof = json.loads((sauces / "project-profile.json").read_text())
    prof["projects"] = ["x"]
    (sauces / "project-profile.json").write_text(json.dumps(prof))
    render(sauces, tmp_path)


def test_gitignore_step_only_when_missing(tmp_path):
    sauces = tmp_path / "proj" / ".sauces"
    shutil.copytree(SAMPLE, sauces)
    assert ".gitignore" in section(render(sauces, tmp_path), "practices")
    (tmp_path / "proj" / ".gitignore").write_text(".sauces/verify/\n")
    assert ".gitignore" not in section(render(sauces, tmp_path), "practices")


def test_script_is_executable():
    assert os.access(REPO / "scripts" / "report_render.py", os.X_OK)


def test_escapes_design_text(tmp_path):
    sauces = tmp_path / ".sauces"
    shutil.copytree(SAMPLE, sauces)
    plan = json.loads((sauces / "plan.json").read_text())
    plan["design_suggestions"][0]["title"] = '<img src=x onerror="alert(1)">'
    (sauces / "plan.json").write_text(json.dumps(plan))
    html = render(sauces, tmp_path)
    assert "<img src=x" not in html
    assert "&lt;img src=x" in html


def test_default_output_path(tmp_path):
    sauces = tmp_path / ".sauces"
    shutil.copytree(SAMPLE, sauces)
    result = run_script("report_render.py", "--sauces-dir", str(sauces))
    assert result.returncode == 0, result.stderr
    assert (sauces / "report.html").is_file()


def test_missing_sauces_dir_is_usage_error(tmp_path):
    result = run_script("report_render.py", "--sauces-dir", str(tmp_path / "nope"))
    assert result.returncode == 2


def test_report_uses_selected_root_when_projects_share_a_platform(tmp_path):
    sauces = tmp_path / ".sauces"
    shutil.copytree(SAMPLE, sauces)
    profile_path = sauces / "project-profile.json"
    profile = json.loads(profile_path.read_text())
    app = profile["projects"][0]
    profile["projects"] = [
        dict(app, root="first-app", architecture="first-app-architecture"),
        dict(app, root="selected-app", architecture="selected-app-architecture"),
    ]
    profile_path.write_text(json.dumps(profile))

    plan_path = sauces / "plan.json"
    plan = json.loads(plan_path.read_text())
    plan["project_root"] = "selected-app"
    plan_path.write_text(json.dumps(plan))

    html = render(sauces, tmp_path)
    assert "selected-app-architecture" in html
    assert "first-app-architecture" not in html


def test_fidelity_shows_web_breakpoint_states(tmp_path):
    sauces = tmp_path / ".sauces"
    shutil.copytree(SAMPLE, sauces)
    summary_path = sauces / "verify" / "summary.json"
    summary = json.loads(summary_path.read_text())
    for r in summary["results"]:
        old = sauces / "verify" / r["id"]
        r["id"] = r["id"].replace("login--", "login@1440--")
        if old.is_dir():
            old.rename(sauces / "verify" / r["id"])
    summary_path.write_text(json.dumps(summary))
    fidelity = section(render(sauces, tmp_path), "fidelity")
    assert "login@1440--default" in fidelity
    assert "Not rendered" not in fidelity
    assert "data:image/png;base64," in fidelity
