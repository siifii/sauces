import json
import time

import pytest

from conftest import run_script

Image = pytest.importorskip("PIL.Image")


def _split_image(path, c1, c2, frac=0.7, size=100):
    img = Image.new("RGB", (size, size), c2)
    img.paste(c1, (0, 0, int(size * frac), size))
    img.save(path)
    return path


def _run(*args):
    r = run_script("extract_palette.py", *map(str, args))
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_two_color_coverage(tmp_path):
    p = _split_image(tmp_path / "a.png", (255, 0, 0), (0, 0, 255))
    out = _run(p)
    assert out["version"] == 1
    colors = out["colors"]
    assert [c["hex"] for c in colors] == ["#FF0000", "#0000FF"]
    assert colors[0]["coverage"] == pytest.approx(0.70, abs=0.02)
    assert colors[1]["coverage"] == pytest.approx(0.30, abs=0.02)
    assert sum(c["coverage"] for c in colors) == pytest.approx(1.0, abs=0.01)


def test_near_duplicates_merge(tmp_path):
    p = _split_image(tmp_path / "a.png", (0x3D, 0x5A, 0xFE), (0x3E, 0x5B, 0xFE), frac=0.5)
    out = _run(p)
    assert len(out["colors"]) == 1
    assert out["colors"][0]["coverage"] == pytest.approx(1.0, abs=0.01)


def test_rgba_and_grayscale(tmp_path):
    rgba = Image.new("RGBA", (50, 50), (0, 0, 0, 0))
    rgba.paste((255, 0, 0, 255), (0, 0, 25, 50))
    rgba.save(tmp_path / "t.png")
    Image.new("L", (20, 20), 128).save(tmp_path / "g.png")
    out = _run(tmp_path / "t.png")
    assert [c["hex"] for c in out["colors"]] == ["#FF0000"]
    out = _run(tmp_path / "g.png")
    assert out["colors"][0]["hex"] == "#808080"
    # fully transparent image -> empty palette, exit 0
    Image.new("RGBA", (10, 10), (1, 2, 3, 0)).save(tmp_path / "blank.png")
    assert _run(tmp_path / "blank.png") == {"version": 1, "colors": []}


def test_multiple_images_pooled_and_output_file(tmp_path):
    a = Image.new("RGB", (10, 10), (255, 0, 0)); a.save(tmp_path / "a.png")
    b = Image.new("RGB", (10, 30), (0, 255, 0)); b.save(tmp_path / "b.png")
    out_file = tmp_path / "o.json"
    r = run_script("extract_palette.py", str(tmp_path / "a.png"), str(tmp_path / "b.png"),
                   "-o", str(out_file))
    assert r.returncode == 0 and r.stdout == ""
    colors = json.loads(out_file.read_text())["colors"]
    assert colors[0]["hex"] == "#00FF00"
    assert colors[0]["coverage"] == pytest.approx(0.75, abs=0.02)


def test_unreadable_file_exits_2(tmp_path):
    bad = tmp_path / "x.png"
    bad.write_text("not an image")
    r = run_script("extract_palette.py", str(bad))
    assert r.returncode == 2
    assert f"cannot read image: {bad}" in r.stderr


def test_large_image_is_fast(tmp_path):
    import numpy as np
    rng = np.random.default_rng(1)
    arr = rng.integers(0, 256, (4000, 4000, 3), dtype=np.uint8)
    Image.fromarray(arr).save(tmp_path / "big.png")
    t = time.time()
    r = run_script("extract_palette.py", str(tmp_path / "big.png"))
    assert r.returncode == 0, r.stderr
    assert time.time() - t < 10
