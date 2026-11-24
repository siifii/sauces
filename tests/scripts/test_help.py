import importlib.util
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conftest import REPO, run_script  # noqa: E402

SCRIPTS = sorted(p.name for p in (REPO / "scripts").glob("*.py"))


@pytest.mark.parametrize("name", SCRIPTS)
def test_every_script_has_help(name):
    r = run_script(name, "--help")
    assert r.returncode == 0, r.stderr
    assert "usage:" in r.stdout


@pytest.mark.parametrize("missing", ["PIL", "numpy"])
def test_missing_dependency_message(monkeypatch, capsys, missing):
    monkeypatch.setitem(sys.modules, missing, None)
    spec = importlib.util.spec_from_file_location("extract_palette", REPO / "scripts" / "extract_palette.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with pytest.raises(SystemExit) as exc:
        mod.require_deps()
    assert exc.value.code == 3
    assert (
        f"Missing dependency: {missing}. Install with: python3 -m pip install pillow numpy"
        in capsys.readouterr().err
    )
