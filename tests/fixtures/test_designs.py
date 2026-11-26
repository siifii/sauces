import json
import xml.etree.ElementTree as ET

from PIL import Image
import numpy as np

from conftest import REPO, needs_pdftoppm, run_script

LOGIN = REPO / "examples" / "designs" / "login"
STATES = ("default", "error", "loading")
PNGS = [LOGIN / f"login--{s}.png" for s in STATES]


def test_design_files():
    for png in PNGS:
        assert png.exists(), png
        with Image.open(png) as im:
            assert im.size == (780, 1688), (png.name, im.size)
    assert (LOGIN / "description.md").exists()
    root = ET.parse(LOGIN / "icons" / "eye.svg").getroot()
    assert root.get("viewBox") == "0 0 24 24"


@needs_pdftoppm
def test_flow_pdf_has_three_pages(tmp_path):
    r = run_script("rasterize_pdf.py", str(LOGIN / "login-flow.pdf"), "--out-dir", str(tmp_path))
    assert r.returncode == 0, r.stderr
    assert len(json.loads(r.stdout)["pages"]) == 3


def test_states_are_distinct():
    arrays = [np.asarray(Image.open(p).convert("RGB"), dtype=int) for p in PNGS]
    for i in range(3):
        for j in range(i + 1, 3):
            assert np.abs(arrays[i] - arrays[j]).sum() > 0, (STATES[i], STATES[j])


def _lab(hex_):
    rgb = np.array([int(hex_[i:i + 2], 16) for i in (1, 3, 5)]) / 255.0
    rgb = np.where(rgb > 0.04045, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
    m = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = m @ rgb / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def test_dominant_color_is_brand():
    r = run_script("extract_palette.py", str(PNGS[0]))
    assert r.returncode == 0, r.stderr
    colors = json.loads(r.stdout)["colors"]
    non_white = [c for c in colors if _lab(c["hex"])[0] < 95]
    assert non_white
    delta = np.linalg.norm(_lab(non_white[0]["hex"]) - _lab("#3D5AFE"))
    assert delta <= 5, (non_white[0], delta)


LOGIN_WEB = REPO / "examples" / "designs" / "login-web"


def test_login_web_design_files():
    for state in STATES:
        with Image.open(LOGIN_WEB / f"login@390--{state}.png") as im:
            assert im.size == (780, 1688)
        with Image.open(LOGIN_WEB / f"login@1440--{state}.png") as im:
            assert im.size == (1440, 900)
        mobile = np.asarray(Image.open(LOGIN / f"login--{state}.png").convert("RGB"))
        copy = np.asarray(Image.open(LOGIN_WEB / f"login@390--{state}.png").convert("RGB"))
        assert np.array_equal(mobile, copy), state
    text = (LOGIN_WEB / "description.md").read_text()
    for copy in ("Welcome back", "Email", "Password", "Forgot password?", "Sign in",
                 "Incorrect email or password", "1440", "390"):
        assert copy in text
    # the mobile sample is untouched
    assert sorted(p.name for p in LOGIN.glob("*.png")) == sorted(p.name for p in PNGS)
