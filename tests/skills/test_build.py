"""Headless tests for the build skill (marker: skill).

One module-scoped pipeline run (scan-project + ingest + plan + build in one flutter-bloc
copy, eval mode) feeds every assertion. The Flutter checks run inside that copy.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import REPO, fixture_copy, needs_claude, needs_flutter, run_script, run_skill

LOGIN = REPO / "examples" / "designs" / "login"
WIDGETS = ("lib/core/widgets/app_button.dart", "lib/core/widgets/app_text_field.dart")

# design-system-patterns.md section 2 (Flutter): layer -> folder regex, for the patterns
# whose `layer` is a name. `follow` layers are folders themselves.
LAYER_FOLDERS = {
    "atomic": {
        "tokens": r"lib/design_system/tokens", "atoms": r"lib/design_system/atoms",
        "molecules": r"lib/design_system/molecules",
        "organisms": r"lib/design_system/organisms",
        "templates": r"lib/design_system/templates", "screens": r"lib/features/[^/]+/view",
    },
    "layered": {
        "tokens": r"lib/design_system/tokens",
        "foundations": r"lib/design_system/foundations",
        "components": r"lib/design_system/components",
        "patterns": r"lib/design_system/patterns", "screens": r"lib/features/[^/]+/view",
    },
    "feature-first": {
        "core-theme": r"lib/core/theme", "core-widgets": r"lib/core/widgets",
        "feature-widgets": r"lib/features/[^/]+/widgets",
        "feature-view": r"lib/features/[^/]+/view",
    },
}

pytestmark = [pytest.mark.skill, needs_claude]


def copy_design(dest):
    """The login PNGs, the eye icon and description.md (no PDF, so no pdftoppm needed)."""
    (dest / "icons").mkdir(parents=True)
    for state in ("default", "error", "loading"):
        shutil.copy(LOGIN / f"login--{state}.png", dest / f"login--{state}.png")
    shutil.copy(LOGIN / "icons" / "eye.svg", dest / "icons" / "eye.svg")
    shutil.copy(LOGIN / "description.md", dest / "description.md")
    return dest


def git(workdir, *args):
    return subprocess.run(["git", *args], cwd=workdir, capture_output=True, text=True,
                          check=True).stdout


def arb_keys(text):
    return {k for k in json.loads(text) if not k.startswith("@")}


def ctor_params(source, cls):
    """Named parameters of the unnamed constructor `cls({...})`: `this.x` and `super.x`."""
    match = re.search(rf"\b(?:const\s+)?{cls}\(\{{(.*?)\}}\)", source, re.S)
    assert match, (cls, source)
    return set(re.findall(r"\b(?:this|super)\.(\w+)", match.group(1)))


def layer_regex(pattern, layer):
    """The folder regex an item's `layer` maps to under the chosen pattern."""
    if pattern == "follow":
        return re.escape(layer.strip("/")).replace(re.escape("<f>"), "[^/]+")
    return LAYER_FOLDERS[pattern][layer]


@pytest.fixture(scope="module")
def pipeline(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("build")
    workdir = fixture_copy("flutter-bloc", tmp)
    design = copy_design(tmp / "design")
    logs = []
    for prompt in ("/sauces:scan-project", f'/sauces:ingest "{design}"', "/sauces:plan",
                   "/sauces:build"):
        result = run_skill(workdir, prompt)
        log = f"$ {prompt}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        logs.append(log)
        assert result.returncode == 0, log
    sauces = workdir / ".sauces"
    state = json.loads((sauces / "state.json").read_text())
    return {
        "workdir": workdir,
        "plan": json.loads((sauces / "plan.json").read_text()),
        "state": state,
        "output": "\n".join(logs),
    }


def added_lines(workdir, path):
    """1-based line numbers build added or changed in an existing file (git diff -U0)."""
    lines = set()
    for hunk in re.finditer(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@",
                            git(workdir, "diff", "-U0", "HEAD", "--", path), re.M):
        start, count = int(hunk.group(1)), int(hunk.group(2) or 1)
        lines.update(range(start, start + count))
    return lines


def test_build_lint_clean(pipeline):
    """Generated files are fully clean; in changed files, every line build wrote is clean.

    Pre-existing literals in the user's files (the fixture's own tests use 'Email') are
    the user's code: build must not rewrite them, so they don't count here.
    """
    state, workdir = pipeline["state"], pipeline["workdir"]
    generated = {f for f in state.get("generated_files", []) if f.endswith(".dart")}
    changed = {f for f in state.get("changed_files", []) if f.endswith(".dart")} - generated
    assert generated | changed, state
    result = run_script("lint_generated.py", "--platform", "flutter",
                        *(str(workdir / f) for f in sorted(generated | changed)))
    assert result.returncode in (0, 1), result.stdout + result.stderr
    findings = []
    for finding in json.loads(result.stdout)["findings"]:
        rel = Path(finding["file"]).resolve().relative_to(workdir.resolve()).as_posix()
        if rel in generated or finding["line"] in added_lines(workdir, rel):
            findings.append(finding)
    assert not findings, json.dumps(findings, indent=2)


@needs_flutter
def test_build_analyzes_and_tests(pipeline):
    workdir = pipeline["workdir"]
    for cmd in (["flutter", "analyze", "--no-fatal-infos"], ["flutter", "test"]):
        result = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=900)
        assert result.returncode == 0, f"{cmd}\n{result.stdout}\n{result.stderr}"


def test_arb_keys_in_all_locales(pipeline):
    l10n = pipeline["workdir"] / "lib" / "l10n"
    en = arb_keys((l10n / "app_en.arb").read_text())
    ar = arb_keys((l10n / "app_ar.arb").read_text())
    assert en == ar, (en ^ ar)
    old = arb_keys(git(pipeline["workdir"], "show", "HEAD:lib/l10n/app_en.arb"))
    assert old <= en, old - en
    assert len(en - old) >= 6, en - old


def test_existing_components_not_replaced(pipeline):
    workdir = pipeline["workdir"]
    for path in WIDGETS:
        assert (workdir / path).is_file(), path
        numstat = git(workdir, "diff", "--numstat", "HEAD", "--", path).split()
        deletions = int(numstat[1]) if numstat else 0
        assert deletions <= 3, (path, numstat, git(workdir, "diff", "HEAD", "--", path))
        cls = "AppButton" if path.endswith("app_button.dart") else "AppTextField"
        old = ctor_params(git(workdir, "show", f"HEAD:{path}"), cls)
        new = ctor_params((workdir / path).read_text(), cls)
        assert old <= new, (path, old - new)


def test_login_page_exists(pipeline):
    sources = [p.read_text() for p in (pipeline["workdir"] / "lib" / "features" / "login")
               .rglob("*.dart")]
    assert any(re.search(r"class\s+LoginPage\s+extends\s+\w*Widget\b", s) for s in sources)
    assert any(re.search(r"class\s+\w+Cubit\s+extends\s+Cubit<", s) for s in sources)


def test_files_follow_structure(pipeline):
    plan, state, workdir = pipeline["plan"], pipeline["state"], pipeline["workdir"]
    pattern = plan["structure"]["choice"]
    items = {i["path"]: i for i in plan["items"]}
    screen_features = {m.group(1) for i in plan["items"] if i["level"] == "screen"
                       for m in [re.match(r"lib/features/([^/]+)/", i["path"])] if m}
    for item in plan["items"]:
        if item["decision"] in ("new", "token"):
            assert (workdir / item["path"]).is_file(), item
    generated = state.get("generated_files", [])
    assert generated, state
    for path in generated:
        assert (workdir / path).exists(), path
        if not path.startswith("lib/"):
            continue
        if path in items:
            item = items[path]
            folder = layer_regex(pattern, item["layer"])
            assert re.match(rf"{folder}/", path), (path, item["layer"], pattern)
            continue
        # Not a plan item: state management beside a planned screen, or l10n output.
        allowed = [rf"lib/features/{re.escape(f)}/(cubit|bloc)/" for f in screen_features]
        allowed.append(r"lib/l10n/")
        assert any(re.match(a, path) for a in allowed), (path, sorted(items))


def test_build_records_state(pipeline):
    workdir, state = pipeline["workdir"], pipeline["state"]
    assert state["stages"]["build"]["status"] == "done", state["stages"]
    todos = json.loads((workdir / ".sauces" / "todos.json").read_text())
    assert isinstance(todos, list) and todos, todos
    for todo in todos:
        lines = (workdir / todo["file"]).read_text().splitlines()
        assert "TODO(sauces)" in lines[todo["line"] - 1], todo
    deviations = json.loads((workdir / ".sauces" / "deviations.json").read_text())
    assert deviations == [], deviations  # eval mode keeps every design suggestion
