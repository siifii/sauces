"""Shared test helpers for the Sauces plugin.

Helpers: run_script, fixture_copy, run_skill, has_tool.
Ready-made skip markers: needs_flutter, needs_pdftoppm, needs_claude.
Import any of these in test files with `from conftest import ...`; that works
because pytest.ini sets `pythonpath = tests`.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def run_script(name: str, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run scripts/<name> with `python3 -I` semantics from the repo root."""
    return subprocess.run(
        [sys.executable, "-I", str(REPO / "scripts" / name), *args],
        cwd=REPO, capture_output=True, text=True, env=env,
    )


def fixture_copy(name: str, tmp_path: Path) -> Path:
    """Copy examples/targets/<name> to tmp_path/'my app' and git init with one commit."""
    dest = tmp_path / "my app"
    shutil.copytree(REPO / "examples" / "targets" / name, dest)
    subprocess.run(["git", "init", "-q"], cwd=dest, check=True)
    subprocess.run(["git", "config", "user.name", "Sauces Test"], cwd=dest, check=True)
    subprocess.run(["git", "config", "user.email", "test@sauces.invalid"], cwd=dest, check=True)
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True)
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
         "commit", "-q", "-m", "fixture"],
        cwd=dest, check=True,
    )
    return dest


def run_skill(workdir: Path, prompt: str, timeout: int = 1800) -> subprocess.CompletedProcess:
    """Run headless claude with the plugin against workdir (use fixture_copy dirs only)."""
    sauces = Path(workdir) / ".sauces"
    sauces.mkdir(parents=True, exist_ok=True)
    (sauces / "eval-approve").write_text("")
    cmd = [
        "claude", "-p", prompt,
        "--plugin-dir", str(REPO),
        "--permission-mode", "bypassPermissions",
        "--strict-mcp-config", "--mcp-config", json.dumps({"mcpServers": {}}),
    ]
    return subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=timeout)


def has_tool(name: str) -> bool:
    return shutil.which(name) is not None


needs_flutter = pytest.mark.skipif(not has_tool("flutter"), reason="flutter not installed")
needs_pdftoppm = pytest.mark.skipif(not has_tool("pdftoppm"), reason="pdftoppm not installed")
needs_claude = pytest.mark.skipif(not has_tool("claude"), reason="claude CLI not installed")
