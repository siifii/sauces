import copy
import json
import shutil

from PIL import Image

from conftest import REPO, run_script

SAMPLE = REPO / "tests/data/sauces_sample"
SCHEMA = REPO / "skills/plan/references/design-diff-schema.json"


def snapshot(dest):
    dest.mkdir(parents=True)
    shutil.copy(SAMPLE / "manifest.json", dest / "manifest.json")
    shutil.copytree(SAMPLE / "references", dest / "references")
    return dest


def edit_manifest(d, fn):
    path = d / "manifest.json"
    manifest = json.loads(path.read_text())
    fn(manifest)
    path.write_text(json.dumps(manifest))


def diff(tmp_path, old, new):
    out = tmp_path / "design-diff.json"
    result = run_script("design_diff.py", "--old", str(old), "--new", str(new), "-o", str(out))
    return result, (json.loads(out.read_text()) if out.exists() else None)


def status(data):
    return {s["id"]: s["status"] for s in data["states"]}


def test_identical_snapshots_are_unchanged(tmp_path):
    old, new = snapshot(tmp_path / "old"), snapshot(tmp_path / "new")
    result, data = diff(tmp_path, old, new)
    assert result.returncode == 0, result.stderr
    assert set(status(data).values()) == {"unchanged"}
    assert data["summary"] == {"changed": 0, "added": 0, "removed": 0, "unchanged": 3}
    assert run_script("check_json.py", str(SCHEMA), str(tmp_path / "design-diff.json")).returncode == 0


def test_pixel_and_size_changes(tmp_path):
    old, new = snapshot(tmp_path / "old"), snapshot(tmp_path / "new")
    ref = new / "references/login--default.png"
    with Image.open(ref) as im:
        im = im.convert("RGB")
        im.paste((0, 0, 0), (0, 0, 300, 300))
        im.save(ref)
    small = new / "references/login--error.png"
    with Image.open(small) as im:
        im.resize((390, 844)).save(small)
    tiny = new / "references/login--loading.png"
    with Image.open(tiny) as im:
        im = im.convert("RGB")
        im.paste((0, 0, 0), (0, 0, 5, 5))
        im.save(tiny)
    _, data = diff(tmp_path, old, new)
    assert status(data) == {"login--default": "changed", "login--error": "changed", "login--loading": "unchanged"}
    reasons = {s["id"]: s["reason"] for s in data["states"]}
    assert "78x169" in reasons["login--error"] and "390x844" in reasons["login--error"]


def test_added_and_removed_states(tmp_path):
    old, new = snapshot(tmp_path / "old"), snapshot(tmp_path / "new")

    def change(m):
        states = m["screens"][0]["states"]
        states.pop(2)
        extra = copy.deepcopy(states[0])
        extra["id"] = "empty"
        extra["reference"] = ".sauces/references/login--default.png"
        states.append(extra)

    edit_manifest(new, change)
    _, data = diff(tmp_path, old, new)
    assert status(data) == {"login--default": "unchanged", "login--error": "unchanged",
                            "login--loading": "removed", "login--empty": "added"}
    assert data["summary"]["added"] == 1 and data["summary"]["removed"] == 1


def test_token_copy_and_asset_changes(tmp_path):
    old, new = snapshot(tmp_path / "old"), snapshot(tmp_path / "new")

    def change(m):
        m["tokens"]["colors"][0]["hex"] = "#112233"
        m["tokens"]["colors"].append({"hex": "#445566", "name": "accent", "origin": "extracted"})
        m["tokens"]["typography"][0]["size"] = 30
        m["tokens"]["spacing"].append(40)
        m["tokens"]["radii"] = []
        m["assets"].append({"path": ".sauces/assets/x.svg", "kind": "icon", "name": "x"})

        def retext(node):
            if isinstance(node, dict):
                if node.get("text") == "Sign in":
                    node["text"] = "Log in"
                for v in node.values():
                    retext(v)
            elif isinstance(node, list):
                for v in node:
                    retext(v)

        retext(m["screens"])

    edit_manifest(new, change)
    _, data = diff(tmp_path, old, new)
    colors = data["tokens"]["colors"]
    assert [c["name"] for c in colors["changed"]] == ["brand"]
    assert [c["name"] for c in colors["added"]] == ["accent"]
    assert [t["name"] for t in data["tokens"]["typography"]["changed"]] == ["title"]
    assert data["tokens"]["spacing"]["added"] == [40]
    assert data["tokens"]["radii"]["removed"] == [12]
    assert [a["name"] for a in data["assets"]["added"]] == ["x"]
    assert {"state": "login--default", "old": "Sign in", "new": "Log in"} in data["copy"]["changed"]
    assert run_script("check_json.py", str(SCHEMA), str(tmp_path / "design-diff.json")).returncode == 0


def test_unreadable_input_exits_2(tmp_path):
    old = snapshot(tmp_path / "old")
    (tmp_path / "new").mkdir()
    result, _ = diff(tmp_path, old, tmp_path / "new")
    assert result.returncode == 2
    assert "manifest.json" in result.stderr
