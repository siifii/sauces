import json
import subprocess

from conftest import REPO, fixture_copy, needs_flutter, run_script

FIXTURE = REPO / "examples" / "targets" / "flutter-bloc"


def flutter(cwd, *args):
    return subprocess.run(["flutter", *args], cwd=cwd, capture_output=True, text=True)


@needs_flutter
def test_fixture_builds(tmp_path):
    app = fixture_copy("flutter-bloc", tmp_path)
    for args in (["pub", "get"], ["analyze", "--no-fatal-infos"], ["test"]):
        result = flutter(app, *args)
        assert result.returncode == 0, f"flutter {' '.join(args)}\n{result.stdout}\n{result.stderr}"
    assert (app / "lib" / "l10n" / "gen" / "app_localizations.dart").exists()


@needs_flutter
def test_fixture_has_exactly_one_lint_gap():
    files = sorted(str(p) for p in (FIXTURE / "lib").rglob("*.dart"))
    assert files
    result = run_script("lint_generated.py", "--platform", "flutter", *files)
    findings = json.loads(result.stdout)
    findings = findings.get("findings", findings) if isinstance(findings, dict) else findings
    assert len(findings) == 1, findings
    assert findings[0]["rule"] == "hardcoded-color"
    assert findings[0]["file"].endswith("lib/core/widgets/app_card.dart")
