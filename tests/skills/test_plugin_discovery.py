"""Compatibility checks for loading the plugin's skills."""
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
