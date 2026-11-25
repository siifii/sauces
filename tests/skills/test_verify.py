"""Tests for the verify skill.

The headless tests (marker: skill) share one module-scoped pipeline run (scan-project +
ingest + plan + build + verify in one flutter-bloc copy, eval mode). The static tests at
the bottom read the shipped skill files and run in the default suite.
"""
import json
import re
import shutil
import subprocess

import pytest
from PIL import Image

from conftest import REPO, fixture_copy, needs_claude, needs_flutter, run_script, run_skill
from test_build import copy_design

SKILL = REPO / "skills" / "verify" / "SKILL.md"
FLUTTER_REF = REPO / "skills" / "verify" / "references" / "flutter.md"
SUMMARY_SCHEMA = REPO / "skills" / "verify" / "references" / "summary-schema.json"
SIZE = (780, 1688)  # 390x844 logical px at device pixel ratio 2


def headless(fn):
    return pytest.mark.skill(needs_claude(needs_flutter(fn)))


@pytest.fixture(scope="module")
def pipeline(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("verify")
    workdir = fixture_copy("flutter-bloc", tmp)
    design = copy_design(tmp / "design")
    logs = []
    # The --threshold argument must be ignored (R2: only .sauces/config.json overrides 90).
    for prompt in ("/sauces:scan-project", f'/sauces:ingest "{design}"', "/sauces:plan",
                   "/sauces:build", "/sauces:verify --threshold 50"):
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


@headless
def test_verify_scores_login(pipeline):
    result = run_script("check_json.py", str(SUMMARY_SCHEMA),
                        str(pipeline["verify"] / "summary.json"))
    assert result.returncode == 0, result.stdout + result.stderr
    default = results_by_id(pipeline["summary"]).get("login--default")
    assert default, pipeline["summary"]
    assert default["rendered"] is True, (default, pipeline["output"])
    assert 1 <= default["iterations"] <= 3, default
    assert default["score"] >= 90, (default, pipeline["output"])
    for r in pipeline["summary"]["results"]:
        if not r["rendered"]:
            continue
        last = pipeline["verify"] / r["id"] / f"iter-{r['iterations']}"
        for name in ("rendered.png", "diff.png", "score.json"):
            assert (last / name).is_file(), last / name
        assert json.loads((last / "score.json").read_text())["score"] == r["score"], r
        # R4: the determinism check ran (two renders on iteration 1) and was recorded.
        assert isinstance(r.get("nondeterministic"), bool), r


@headless
def test_rtl_render_exists(pipeline):
    rendered = [r for r in pipeline["summary"]["results"] if r["rendered"]]
    assert rendered, pipeline["summary"]
    for r in rendered:
        assert (pipeline["verify"] / r["id"] / "rtl.png").is_file(), r["id"]


@headless
def test_render_sizes(pipeline):
    images = sorted(pipeline["verify"].glob("*/iter-*/rendered.png"))
    rtl = sorted(pipeline["verify"].glob("*/rtl.png"))
    assert images and rtl, pipeline["verify"]
    for path in images + rtl:
        with Image.open(path) as img:
            assert img.size == SIZE, (path, img.size)


@headless
def test_verify_does_not_change_thresholds(pipeline):
    assert pipeline["summary"]["threshold"] == 90, pipeline["summary"]
    scores = sorted(pipeline["verify"].glob("*/iter-*/score.json"))
    assert scores, pipeline["verify"]
    for path in scores:
        assert json.loads(path.read_text())["threshold"] == 90, path


@headless
def test_verify_records_state(pipeline):
    assert pipeline["state"]["stages"]["verify"]["status"] == "done", pipeline["state"]
    tests = [f for f in pipeline["state"].get("generated_files", [])
             if re.fullmatch(r"test/sauces/[a-z0-9_]+_render_test\.dart", f)]
    assert tests, pipeline["state"]
    for rel in tests:
        path = pipeline["workdir"] / rel
        assert path.is_file(), path
        src = path.read_text()
        assert "SAUCES_RENDER_DIR" in src, rel
        assert "pumpAndSettle(" not in src, rel
        assert "MaterialIcons-Regular.otf" in src, rel
        assert "FlutterError.onError" in src, rel
    assert not (pipeline["verify"] / "_render").exists()


# Static checks on the shipped skill (default suite).

def test_threshold_comes_only_from_config():
    text = SKILL.read_text()
    front = text.split("---")[1]
    assert "argument-hint" not in front
    assert "fidelity_threshold" in text and ".sauces/config.json" in text
    assert not re.search(r"--threshold <n>|\$ARGUMENTS contains `--threshold", text)


def test_reference_render_template():
    text = FLUTTER_REF.read_text()
    dart = re.search(r"```dart\n(.*?)```", text, re.S).group(1)
    assert "pumpAndSettle(" not in dart
    assert "bin/cache/artifacts/material_fonts/MaterialIcons-Regular.otf" in dart
    assert "FontLoader('MaterialIcons')" in dart
    # I5: the PNG is written before the test can fail on collected errors.
    assert "FlutterError.onError" in dart
    assert dart.index("writeAsBytesSync") < dart.index("expect(")
    # M1: every state gets an LTR and an RTL test.
    assert "--rtl" in dart and "for (final" in dart
    # M2: the per-screen loop runs one file, not the whole folder.
    assert re.search(r"flutter test --dart-define=\S+ \"?test/sauces/<screen>_render_test\.dart", text)


@needs_flutter
def test_flutter_render_writes_rtl_overflow_diagnostics(tmp_path):
    source = REPO / "examples" / "targets" / "flutter-bloc"
    if not (source / ".dart_tool" / "package_config.json").is_file():
        pytest.skip("run flutter pub get in examples/targets/flutter-bloc first")
    project = tmp_path / "project"
    shutil.copytree(source, project, ignore=shutil.ignore_patterns("build", ".git"))
    reference = FLUTTER_REF.read_text()
    dart = re.search(r"```dart\n(.*?)```", reference, re.S).group(1)
    render = dart[dart.index("const _renderDir"):dart.index("\nWidget _login")]
    render = render.replace("AppTheme.light()", "ThemeData()")
    render = render.replace("          AppLocalizations.delegate,\n", "")
    render = render.replace(
        "supportedLocales: AppLocalizations.supportedLocales,",
        "supportedLocales: const [Locale('en'), Locale('ar')],",
    )
    test = project / "test" / "sauces_template_test.dart"
    test.parent.mkdir(exist_ok=True)
    test.write_text(
        """import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';

"""
        + render
        + """
void main() {
  testWidgets('clean RTL', (t) => _render(t, const SizedBox(), 'clean--rtl',
      locale: const Locale('ar')));
  testWidgets('overflow RTL', (t) => _render(t, Builder(builder: (context) {
    FlutterError.reportError(FlutterErrorDetails(
      exception: FlutterError('A RenderFlex overflowed by 42 pixels on the bottom.'),
    ));
    return const SizedBox();
  }), 'broken--rtl', locale: const Locale('ar')));
}
"""
    )
    output = tmp_path / "renders"
    output.mkdir()
    (output / "clean--rtl.errors.txt").write_text("stale error")
    result = subprocess.run(
        ["flutter", "test", "--no-pub", f"--dart-define=SAUCES_RENDER_DIR={output}",
         "test/sauces_template_test.dart"],
        cwd=project, capture_output=True, text=True, timeout=180,
    )
    log = result.stdout + result.stderr
    assert result.returncode != 0, log
    assert (output / "clean--rtl.png").is_file(), log
    assert (output / "broken--rtl.png").is_file(), log
    assert (output / "clean--rtl.errors.txt").read_text() == ""
    assert "overflowed" in (output / "broken--rtl.errors.txt").read_text().lower()
