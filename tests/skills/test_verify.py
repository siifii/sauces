"""Headless tests for the verify skill (marker: skill).

One module-scoped pipeline run (scan-project + ingest + plan + build + verify in one
flutter-bloc copy, eval mode) feeds every assertion.
"""
import json

import pytest
from PIL import Image

from conftest import REPO, fixture_copy, needs_claude, needs_flutter, run_script, run_skill
from test_build import copy_design

SUMMARY_SCHEMA = REPO / "skills" / "verify" / "references" / "summary-schema.json"

pytestmark = [pytest.mark.skill, needs_claude, needs_flutter]


@pytest.fixture(scope="module")
def pipeline(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("verify")
    workdir = fixture_copy("flutter-bloc", tmp)
    design = copy_design(tmp / "design")
    logs = []
    for prompt in ("/sauces:scan-project", f'/sauces:ingest "{design}"', "/sauces:plan",
                   "/sauces:build", "/sauces:verify"):
        result = run_skill(workdir, prompt)
        log = f"$ {prompt}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        logs.append(log)
        assert result.returncode == 0, log
    verify = workdir / ".sauces" / "verify"
    return {
        "workdir": workdir,
        "verify": verify,
        "summary": json.loads((verify / "summary.json").read_text()),
        "state": json.loads((workdir / ".sauces" / "state.json").read_text()),
        "output": "\n".join(logs),
    }


def results_by_id(summary):
    return {r["id"]: r for r in summary["results"]}


def test_verify_scores_login(pipeline):
    result = run_script("check_json.py", str(SUMMARY_SCHEMA),
                        str(pipeline["verify"] / "summary.json"))
    assert result.returncode == 0, result.stdout + result.stderr
    default = results_by_id(pipeline["summary"]).get("login--default")
    assert default, pipeline["summary"]
    assert default["rendered"] is True, (default, pipeline["output"])
    assert 1 <= default["iterations"] <= 3, default
    assert default["score"] >= 90, (default, pipeline["output"])
    last = pipeline["verify"] / "login--default" / f"iter-{default['iterations']}"
    for name in ("rendered.png", "diff.png", "score.json"):
        assert (last / name).is_file(), last / name
    assert json.loads((last / "score.json").read_text())["score"] == default["score"]


def test_rtl_render_exists(pipeline):
    rendered = [r for r in pipeline["summary"]["results"] if r["rendered"]]
    assert rendered, pipeline["summary"]
    for r in rendered:
        rtl = pipeline["verify"] / r["id"] / "rtl.png"
        assert rtl.is_file(), rtl
        with Image.open(rtl) as img:
            assert img.size == (780, 1688), (rtl, img.size)


def test_verify_does_not_change_thresholds(pipeline):
    scores = sorted(pipeline["verify"].glob("*/iter-*/score.json"))
    assert scores, pipeline["verify"]
    for path in scores:
        assert json.loads(path.read_text())["threshold"] == 90, path


def test_verify_records_state(pipeline):
    assert pipeline["state"]["stages"]["verify"]["status"] == "done", pipeline["state"]
    goldens = [f for f in pipeline["state"].get("generated_files", [])
               if f.startswith("test/sauces/")]
    assert goldens, pipeline["state"]
