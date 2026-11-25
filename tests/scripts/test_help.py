import importlib.util
import sys

import pytest

from conftest import REPO, run_script

SCRIPTS = sorted(p.name for p in (REPO / "scripts").glob("*.py"))


def _load(name):
    spec = importlib.util.spec_from_file_location(name[:-3], REPO / "scripts" / name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Scripts that declare require_deps need Pillow/numpy; stdlib-only scripts (check_json) don't.
DEP_SCRIPTS = sorted(n for n in SCRIPTS if "def require_deps" in (REPO / "scripts" / n).read_text())


@pytest.mark.parametrize("name", SCRIPTS)
def test_every_script_has_help(name):
    r = run_script(name, "--help")
    assert r.returncode == 0, r.stderr
    assert "usage:" in r.stdout


@pytest.mark.parametrize("name", DEP_SCRIPTS)
@pytest.mark.parametrize("missing", ["PIL", "numpy"])
def test_missing_dependency_message(monkeypatch, capsys, name, missing):
    monkeypatch.setitem(sys.modules, missing, None)
    mod = _load(name)
    with pytest.raises(SystemExit) as exc:
        mod.require_deps()
    assert exc.value.code == 3
    assert (
        f"Missing dependency: {missing}. Install with: python3 -m pip install pillow numpy"
        in capsys.readouterr().err
    )
