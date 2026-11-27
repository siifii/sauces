"""Dark mode as a first-class appearance: schema, references, sample design."""
import copy
import json

from PIL import Image

from conftest import REPO, run_script

SAMPLE = REPO / "tests/data/sauces_sample"
DARK = REPO / "examples/designs/login-dark"
PLATFORMS = ("flutter", "android-compose", "ios-swiftui", "kmp-cmp", "react-native", "web-react", "web-html")


def test_manifest_accepts_appearance(tmp_path):
    manifest = json.loads((SAMPLE / "manifest.json").read_text())
    dark = copy.deepcopy(manifest["screens"][0]["states"][0])
    dark.update(id="default-dark", appearance="dark")
    manifest["screens"][0]["states"].append(dark)
    path = tmp_path / "m.json"
    path.write_text(json.dumps(manifest))
    schema = REPO / "skills/ingest/references/manifest-schema.json"
    assert run_script("check_json.py", str(schema), str(path)).returncode == 0
    dark["appearance"] = "dim"
    path.write_text(json.dumps(manifest))
    assert run_script("check_json.py", str(schema), str(path)).returncode == 1


def test_dark_mode_reference_covers_pipeline_and_platforms():
    text = (REPO / "skills/plan/references/dark-mode.md").read_text()
    for needle in ("appearance", "-dark", "## Ingest", "## Plan", "## Build", "## Verify",
                   "recommendation", "never invent", "contrast"):
        assert needle in text, needle
    for platform in PLATFORMS:
        assert f"**{platform}" in text, platform
    for skill in ("ingest", "plan", "verify"):
        assert "dark-mode.md" in (REPO / f"skills/{skill}/SKILL.md").read_text(), skill


def test_login_dark_sample():
    for state in ("default", "error", "loading"):
        for suffix in ("", "-dark"):
            with Image.open(DARK / f"login--{state}{suffix}.png") as im:
                assert im.size == (780, 1688)
    with Image.open(DARK / "login--default-dark.png") as im:
        assert im.convert("RGB").getpixel((10, 10)) == (0x1B, 0x1B, 0x1F)
    text = (DARK / "description.md").read_text()
    assert "#1B1B1F" in text and "dark" in text
