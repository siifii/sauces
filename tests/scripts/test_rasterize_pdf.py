import json
from pathlib import Path

from PIL import Image

from conftest import needs_pdftoppm, run_script


def make_pdf(path: Path, pages: int) -> Path:
    imgs = [Image.new("RGB", (200, 300), (20 * i % 255, 100, 200)) for i in range(pages)]
    imgs[0].save(path, save_all=True, append_images=imgs[1:])
    return path


@needs_pdftoppm
def test_two_page_pdf(tmp_path):
    pdf = make_pdf(tmp_path / "in.pdf", 2)
    out = tmp_path / "out"
    r = run_script("rasterize_pdf.py", str(pdf), "--out-dir", str(out))
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data == {"version": 1, "pages": [f"{out}/page-001.png", f"{out}/page-002.png"]}
    for p in data["pages"]:
        assert Image.open(p).format == "PNG"


@needs_pdftoppm
def test_twelve_pages_in_order_and_stale_cleanup(tmp_path):
    pdf = make_pdf(tmp_path / "in.pdf", 12)
    out = tmp_path / "out"
    out.mkdir()
    (out / "page-099.png").write_bytes(b"stale")
    (out / "keep.png").write_bytes(b"keep")
    r = run_script("rasterize_pdf.py", str(pdf), "--out-dir", str(out))
    assert r.returncode == 0, r.stderr
    pages = json.loads(r.stdout)["pages"]
    assert pages == [f"{out}/page-{i:03d}.png" for i in range(1, 13)]
    assert not (out / "page-099.png").exists()
    assert (out / "keep.png").read_bytes() == b"keep"
    assert sorted(x.name for x in out.iterdir()) == ["keep.png"] + [f"page-{i:03d}.png" for i in range(1, 13)]


def test_missing_pdftoppm(tmp_path):
    pdf = make_pdf(tmp_path / "in.pdf", 1)
    r = run_script("rasterize_pdf.py", str(pdf), "--out-dir", str(tmp_path / "o"), env={"PATH": ""})
    assert r.returncode == 4
    assert "pdftoppm not found. Install poppler (macOS: brew install poppler; Debian/Ubuntu: apt install poppler-utils)." in r.stderr


def test_missing_pdf(tmp_path):
    r = run_script("rasterize_pdf.py", str(tmp_path / "nope.pdf"), "--out-dir", str(tmp_path / "o"))
    assert r.returncode == 2
    assert f"PDF not found: {tmp_path / 'nope.pdf'}" in r.stderr


@needs_pdftoppm
def test_corrupt_pdf_fails(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_text("not a pdf")
    r = run_script("rasterize_pdf.py", str(bad), "--out-dir", str(tmp_path / "o"))
    assert r.returncode == 1
    assert "pdftoppm failed: " in r.stderr
