"""Keep platform routes, schemas and the generated-code lint CLI aligned."""

import json
import subprocess
import sys

import pytest

from conftest import REPO


ADDITIONAL_PLATFORMS = [
    ("android-compose", "kt", 'Text(text = "Continue")\nval tint = Color(0xFFFFFFFF)'),
    ("ios-swiftui", "swift", 'Text(verbatim: "Continue")\nlet tint = Color(red: 1, green: 1, blue: 1)'),
    ("react-native", "tsx", '<Text>Continue</Text>\nconst style = {color: "#ffffff"}'),
    ("kmp-cmp", "kt", 'Text("Continue")\nval tint = Color(0xFFFFFFFF)'),
]


@pytest.mark.parametrize("platform,extension,source", ADDITIONAL_PLATFORMS)
def test_native_platform_has_workflow_and_lint(platform, extension, source, tmp_path):
    for skill, schema in (
        ("scan-project", "profile-schema.json"),
        ("plan", "plan-schema.json"),
        ("verify", "summary-schema.json"),
    ):
        properties = json.loads((REPO / "skills" / skill / "references" / schema).read_text())["properties"]
        if skill == "scan-project":
            properties = properties["projects"]["items"]["properties"]
        assert platform in properties["platform"]["enum"]

    for skill in ("scan-project", "scaffold", "build", "verify"):
        assert (REPO / "skills" / skill / "references" / f"{platform}.md").is_file()

    path = tmp_path / f"Screen.{extension}"
    path.write_text(source, encoding="utf-8")
    command = [sys.executable, "-I", str(REPO / "scripts/lint_generated.py"), "--platform", platform]
    for options, expected in (
        ([], ["hardcoded-string", "hardcoded-color"]),
        (["--allow-colors", "Screen.*"], ["hardcoded-string"]),
    ):
        result = subprocess.run(
            [*command, *options, path.name], cwd=tmp_path, capture_output=True, text=True,
        )
        assert result.returncode == 1, result.stderr
        assert [finding["rule"] for finding in json.loads(result.stdout)["findings"]] == expected
