"""Headless tests for the ingest skill (marker: skill)."""
import json

import pytest

from conftest import REPO, fixture_copy, needs_claude, needs_pdftoppm, run_script, run_skill

SCHEMA = REPO / "skills" / "ingest" / "references" / "manifest-schema.json"
LOGIN = REPO / "examples" / "designs" / "login"
FIGMA_URL = "https://www.figma.com/design/AbCdEf123/Login?node-id=1-2"
FIGMA_REASON = "No Figma MCP connected. Connect the Figma connector or the plugin's figma server."

pytestmark = [pytest.mark.skill, needs_claude]


def hex_to_lab(hex_color):
    rgb = [int(hex_color.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    x = (0.4124 * lin[0] + 0.3576 * lin[1] + 0.1805 * lin[2]) / 0.95047
    y = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    z = (0.0193 * lin[0] + 0.1192 * lin[1] + 0.9505 * lin[2]) / 1.08883
    f = [t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in (x, y, z)]
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])


def delta_e(a, b):
    return sum((p - q) ** 2 for p, q in zip(hex_to_lab(a), hex_to_lab(b))) ** 0.5


def layout_texts(node):
    """Every `text` value in a layout tree."""
    if isinstance(node, dict):
        found = [node["text"]] if isinstance(node.get("text"), str) else []
        for value in node.values():
            found += layout_texts(value)
        return found
    if isinstance(node, list):
        return [t for item in node for t in layout_texts(item)]
    return []


def nodes(node):
    """Every node dict in a layout tree (depth first)."""
    if not isinstance(node, dict):
        return []
    found = [node]
    for child in node.get("children") or []:
        found += nodes(child)
    return found


def left_padding(style):
    pad = (style or {}).get("padding")
    if isinstance(pad, (int, float)):
        return pad
    if isinstance(pad, list) and len(pad) == 4:
        return pad[3]
    if isinstance(pad, list) and len(pad) == 2:
        return pad[1]
    return None


def copy_login_pngs(folder):
    folder.mkdir()
    for state in ("default", "error", "loading"):
        (folder / f"login--{state}.png").write_bytes((LOGIN / f"login--{state}.png").read_bytes())


def ingest(workdir, sources):
    result = run_skill(workdir, "/sauces:ingest " + " ".join(f'"{s}"' for s in sources))
    manifest_path = workdir / ".sauces" / "manifest.json"
    assert manifest_path.is_file(), (
        f"no manifest written\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    check = run_script("check_json.py", str(SCHEMA), str(manifest_path))
    assert check.returncode == 0, check.stdout + check.stderr
    return json.loads(manifest_path.read_text()), result


def login_screen(manifest, workdir):
    screens = [s for s in manifest["screens"] if s["id"] == "login"]
    assert len(screens) == 1, manifest["screens"]
    states = {st["name"]: st for st in screens[0]["states"]}
    assert set(states) == {"default", "error", "loading"}, screens[0]["states"]
    assert len(screens[0]["states"]) == 3, screens[0]["states"]
    for name, st in states.items():
        assert st["reference"] == f".sauces/references/login--{name}.png", st
        assert (workdir / st["reference"]).is_file(), st["reference"]
    return states


@needs_pdftoppm
def test_ingest_login(tmp_path):
    workdir = fixture_copy("flutter-bloc", tmp_path)
    manifest, _ = ingest(workdir, [str(LOGIN)])

    states = login_screen(manifest, workdir)
    pdfs = [s for s in manifest["sources"] if s["kind"] == "pdf"]
    assert len(pdfs) == 1 and pdfs[0]["status"] == "ok", manifest["sources"]
    assert not [s for s in manifest["sources"] if "/src/" in s["ref"]], manifest["sources"]
    eye = [a for a in manifest["assets"] if a["name"] == "eye" and a["kind"] == "icon"]
    assert eye, manifest["assets"]
    assert eye[0]["path"] == ".sauces/assets/eye.svg" and (workdir / eye[0]["path"]).is_file(), eye
    assert manifest["tokens"]["typography"], manifest["tokens"]
    assert any(delta_e(c["hex"], "#3D5AFE") <= 5 for c in manifest["tokens"]["colors"]), (
        manifest["tokens"]["colors"]
    )
    texts = layout_texts(states["default"].get("layout", {}))
    assert any("Welcome back" in t for t in texts), texts
    assert any("Sign in" in t for t in texts), texts
    candidates = manifest.get("design_system", {}).get("component_candidates", [])
    by_kind = {}
    for c in candidates:
        key = c["name"].lower().replace("-", "").replace("_", "").replace(" ", "")
        by_kind[key] = max(by_kind.get(key, 0), c["occurrences"])
    assert by_kind.get("textfield", 0) >= 3, candidates
    assert by_kind.get("button", 0) >= 3, candidates


def test_ingest_figma_without_mcp(tmp_path):
    workdir = fixture_copy("flutter-bloc", tmp_path)
    png_folder = tmp_path / "pngs"
    copy_login_pngs(png_folder)
    manifest, result = ingest(workdir, [FIGMA_URL, str(png_folder)])

    assert result.returncode == 0, result.stdout + result.stderr
    figma = [s for s in manifest["sources"] if s["kind"] == "figma"]
    assert len(figma) == 1, manifest["sources"]
    assert figma[0]["status"] == "unreadable", figma[0]
    assert "Figma" in figma[0].get("reason", ""), figma[0]
    assert FIGMA_REASON in figma[0]["reason"], figma[0]
    login_screen(manifest, workdir)


def test_ingest_pngs_only_measures(tmp_path):
    """Only the three PNGs (no description.md, no src/): values must be measured from pixels."""
    workdir = fixture_copy("flutter-bloc", tmp_path)
    png_folder = tmp_path / "pngs"
    copy_login_pngs(png_folder)
    manifest, _ = ingest(workdir, [str(png_folder)])

    states = login_screen(manifest, workdir)
    layout = states["default"].get("layout", {})
    texts = layout_texts(layout)
    assert any("Welcome back" in t for t in texts), texts
    all_nodes = nodes(layout)
    buttons = [n for n in all_nodes if (n.get("component") or {}).get("kind") == "button"]
    assert buttons, layout
    heights = [(b.get("style") or {}).get("height") for b in buttons]
    assert any(isinstance(h, (int, float)) and 46 <= h <= 58 for h in heights), heights
    pads = [left_padding(n.get("style")) for n in all_nodes]
    assert any(isinstance(p, (int, float)) and 20 <= p <= 28 for p in pads), pads
    assert any(delta_e(c["hex"], "#3D5AFE") <= 5 for c in manifest["tokens"]["colors"]), (
        manifest["tokens"]["colors"]
    )
