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


PLAYWRIGHT = "playwright@1.61.1"


def free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_web_html_fixture_loads_in_both_directions(tmp_path):
    import sys
    import time
    from PIL import Image

    site = REPO / "examples" / "targets" / "web-html"
    port = free_port()
    server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
                              cwd=site, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(1)
        for lang in ("en", "ar"):
            out = tmp_path / f"{lang}.png"
            run(tmp_path, "npx", "-y", PLAYWRIGHT, "screenshot", "--viewport-size=390,844",
                "--wait-for-timeout=500", f"http://127.0.0.1:{port}/?lang={lang}", str(out))
            with Image.open(out) as im:
                assert im.size == (390, 844)
    finally:
        server.terminate()
        server.wait()
    assert not (site / "package.json").exists()
    assert not (site / "node_modules").exists()
