import json
import sys
import time

import numpy as np
import pytest
from PIL import Image

from conftest import run_script

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2] / "scripts"))
import visual_diff  # noqa: E402


def _gradient(w, h):
    x = np.linspace(0, 255, w, dtype=np.float64)[None, :]
    y = np.linspace(0, 255, h, dtype=np.float64)[:, None]
    r = np.broadcast_to(x, (h, w))
    g = np.broadcast_to(y, (h, w))
    b = (r + g) / 2
    return np.stack([r, g, b], axis=-1).astype(np.uint8)


def _save(arr, path):
    Image.fromarray(arr).save(path)
    return str(path)


def _run(tmp_path, rendered, reference, *extra):
    out = tmp_path / "out"
    r = run_script("visual_diff.py", rendered, reference, "--out-dir", str(out), *extra)
    return r, out


def test_identical_is_100(tmp_path):
    p = _save(_gradient(60, 80), tmp_path / "a.png")
    r, out = _run(tmp_path, p, p)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "100.0"
    data = json.loads((out / "score.json").read_text())
    assert data["score"] == 100.0 and data["passed"] is True and data["version"] == 1


def test_inverted_is_low(tmp_path):
    a = _gradient(60, 80)
    ra = _save(a, tmp_path / "a.png")
    rb = _save(255 - a, tmp_path / "b.png")
    r, out = _run(tmp_path, ra, rb)
    assert float(r.stdout.strip()) < 30


def test_size_mismatch_resizes(tmp_path):
    small = _save(_gradient(390, 844), tmp_path / "s.png")
    big = _save(_gradient(780, 1688), tmp_path / "b.png")
    r, out = _run(tmp_path, small, big)
    assert r.returncode in (0, 1), r.stderr
    data = json.loads((out / "score.json").read_text())
    assert data["size"] == [780, 1688]
    assert Image.open(out / "diff.png").size == (780, 1688)


def test_rgba_transparent_vs_white_is_100(tmp_path):
    t = _save(np.zeros((40, 40, 4), dtype=np.uint8), tmp_path / "t.png")
    w = _save(np.full((40, 40, 3), 255, dtype=np.uint8), tmp_path / "w.png")
    r, out = _run(tmp_path, t, w)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "100.0"


def test_writes_outputs_and_exit_code(tmp_path):
    a = _gradient(60, 80)
    ra = _save(a, tmp_path / "a.png")
    rb = _save(255 - a, tmp_path / "b.png")
    r, out = _run(tmp_path, ra, rb)
    assert r.returncode == 1
    data = json.loads((out / "score.json").read_text())
    assert data["passed"] is False
    assert (out / "diff.png").exists()
    assert set(data) == {"version", "score", "pixel_similarity", "ssim", "threshold", "passed", "size"}


def test_threshold_lowered_passes(tmp_path):
    a = _gradient(60, 80)
    ra = _save(a, tmp_path / "a.png")
    rb = _save(255 - a, tmp_path / "b.png")
    r, _ = _run(tmp_path, ra, rb, "--threshold", "0")
    assert r.returncode == 0


def test_bad_inputs_exit_2(tmp_path):
    p = _save(_gradient(20, 20), tmp_path / "a.png")
    r, _ = _run(tmp_path, str(tmp_path / "missing.png"), p)
    assert r.returncode == 2 and "cannot read image" in r.stderr
    r, _ = _run(tmp_path, p, p, "--threshold", "101")
    assert r.returncode == 2


def test_tiny_reference_uses_pixel_similarity():
    a = np.zeros((5, 5, 3), dtype=np.uint8)
    assert visual_diff.ssim(a, a) == 1.0
    assert visual_diff.score(1.0, 1.0) == 100.0


def test_large(tmp_path):
    rng = np.random.default_rng(0)
    a = rng.integers(0, 256, (1688, 780, 3), dtype=np.uint8)
    b = np.clip(a.astype(int) + 10, 0, 255).astype(np.uint8)
    pa, pb = _save(a, tmp_path / "a.png"), _save(b, tmp_path / "b.png")
    t = time.time()
    r, _ = _run(tmp_path, pa, pb)
    assert r.returncode in (0, 1), r.stderr
    assert time.time() - t < 5
