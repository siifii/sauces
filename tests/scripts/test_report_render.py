import json
import re
import shutil

import pytest

from conftest import REPO, run_script

SAMPLE = REPO / "tests" / "data" / "sauces_sample"
SECTIONS = ("summary", "fidelity", "design-system", "graph", "localization", "audit", "todos",
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


def test_localization_counts(sample_html):
    loc = section(sample_html, "localization")
    assert re.search(r"\b5\b.*?added", loc, re.S), loc
    assert re.search(r"\b1\b.*?reused", loc, re.S), loc
    assert "Forgot password? stays right-aligned" in loc


def test_self_contained(sample_html):
    assert not re.search(r"<link[^>]+rel=[\"']?stylesheet", sample_html, re.I)
    external = re.findall(r"""\bsrc=["'](https?://[^"']+)""", sample_html)
    assert len(external) == 1 and "mermaid" in external[0], external
    assert "graph LR" in section(sample_html, "graph")  # <pre> fallback with the source


def test_missing_inputs(tmp_path):
    sauces = tmp_path / ".sauces"
    sauces.mkdir()
    shutil.copy(SAMPLE / "manifest.json", sauces / "manifest.json")
    html = render(sauces, tmp_path)
    for sid in SECTIONS:
        section(html, sid)
    assert "not run" in html


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
