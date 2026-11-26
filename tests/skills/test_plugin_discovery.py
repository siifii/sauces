"""Compatibility checks for loading the plugin's skills."""
import json
import os
import shutil
import subprocess

import pytest

from conftest import REPO


@pytest.mark.skipif(shutil.which("copilot") is None, reason="copilot CLI not installed")
def test_scaffold_is_discoverable_by_copilot():
    env = {**os.environ, "COPILOT_PLUGIN_DIR_ONLY": "true"}
    result = subprocess.run(
        ["copilot", "--plugin-dir", str(REPO), "skill", "list"],
        cwd=REPO, env=env, capture_output=True, text=True,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "skills/scaffold/SKILL.md: failed to parse" not in output, output
    assert "  scaffold - " in output, output


def test_manifest_mentions_web():
    data = json.loads((REPO / ".claude-plugin/plugin.json").read_text())
    assert {"react", "nextjs", "html", "css", "web"} <= set(data["keywords"])
    assert "web" in data["description"].lower()
    section7 = (REPO / "docs/superpowers/spec.md").read_text().split("## 7.")[1].split("## 8.")[0]
    assert "Web targets" not in section7
    readme = (REPO / "README.md").read_text()
    assert "web-react" in readme and "web-html" in readme
    claude_md = (REPO / "CLAUDE.md").read_text()
    assert "| Web (React) |" in claude_md and "| Web (HTML) |" in claude_md
