"""Opt-in web fixture checks (`-m web`): install, build, test and capture the web fixtures.

Needs Node (npx) and network for `npm ci`. Select with `.venv/bin/pytest -m web`.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import REPO

pytestmark = [
    pytest.mark.web,
    pytest.mark.skipif(shutil.which("npx") is None, reason="npx not installed"),
]

SKIP_DIRS = ("node_modules", ".next", "dist")


def copy_web(name: str, tmp_path: Path) -> Path:
    """Copy examples/targets/<name> to tmp_path/<name>, leaving out build output."""
    dest = tmp_path / name
    shutil.copytree(REPO / "examples" / "targets" / name, dest,
                    ignore=shutil.ignore_patterns(*SKIP_DIRS))
    return dest


def run(cwd: Path, *cmd: str) -> bytes:
    """Run cmd in cwd; raise with its output on failure."""
    r = subprocess.run(list(cmd), cwd=cwd, capture_output=True, timeout=900)
    if r.returncode != 0:
        raise AssertionError(f"{' '.join(cmd)} failed ({r.returncode}):\n"
                             f"{r.stdout.decode(errors='replace')[-4000:]}\n"
                             f"{r.stderr.decode(errors='replace')[-4000:]}")
    return r.stdout


@pytest.mark.parametrize("name", ["web-react-vite", "web-react-next"])
def test_react_fixture_builds(name, tmp_path):
    app = copy_web(name, tmp_path)
    run(app, "npm", "ci", "--no-audit", "--no-fund")
    run(app, "npm", "run", "typecheck")
    run(app, "npm", "run", "build")
    if name == "web-react-vite":
        run(app, "npm", "test")
