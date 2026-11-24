import json
import shutil

from conftest import REPO, run_script

SCHEMA = str(REPO / "skills/cook/references/state-schema.json")
STAGES = ["ingest", "scan", "plan", "build", "verify", "report"]


def nxt(root, h):
    r = run_script("sauces_state.py", "next", "--root", str(root), "--inputs-hash", h)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def mark(root, stage, h=None):
    args = ["mark", stage, "--root", str(root)]
    if h:
        args += ["--inputs-hash", h]
    return run_script("sauces_state.py", *args)


def test_fresh_project_next_is_ingest(tmp_path):
    assert nxt(tmp_path, "A") == "ingest"


def test_after_all_marked_next_is_done(tmp_path):
    for s in STAGES:
        assert mark(tmp_path, s, "A").returncode == 0
    assert nxt(tmp_path, "A") == "done"


def test_resume_at_first_pending(tmp_path):
    mark(tmp_path, "ingest", "A")
    mark(tmp_path, "scan")
    assert nxt(tmp_path, "A") == "plan"


def test_changed_sources_restart_at_ingest(tmp_path):
    for s in STAGES:
        mark(tmp_path, s, "A")
    assert nxt(tmp_path, "B") == "ingest"


def test_reset_from_invalidates_downstream(tmp_path):
    for s in STAGES:
        mark(tmp_path, s, "A")
    r = run_script("sauces_state.py", "reset-from", "plan", "--root", str(tmp_path))
    assert r.returncode == 0, r.stderr
    assert nxt(tmp_path, "A") == "plan"
    stages = json.loads((tmp_path / ".sauces/state.json").read_text())["stages"]
    assert [stages[s]["status"] for s in STAGES] == ["done", "done"] + ["pending"] * 4
    assert stages["build"]["finished_at"] is None


def test_ingest_requires_inputs_hash(tmp_path):
    assert mark(tmp_path, "ingest").returncode == 2


def test_unknown_stage_exits_2(tmp_path):
    assert mark(tmp_path, "bogus", "A").returncode == 2
    r = run_script("sauces_state.py", "reset-from", "bogus", "--root", str(tmp_path))
    assert r.returncode == 2


def test_add_files_dedupes(tmp_path):
    for _ in range(2):
        r = run_script("sauces_state.py", "add-files", "generated",
                       "lib/a.dart", "lib/b.dart", "--root", str(tmp_path))
        assert r.returncode == 0, r.stderr
    run_script("sauces_state.py", "add-files", "changed", "pubspec.yaml", "--root", str(tmp_path))
    st = json.loads((tmp_path / ".sauces/state.json").read_text())
    assert st["generated_files"] == ["lib/a.dart", "lib/b.dart"]
    assert st["changed_files"] == ["pubspec.yaml"]


def test_state_validates_against_schema(tmp_path):
    mark(tmp_path, "ingest", "A")
    run_script("sauces_state.py", "add-files", "generated", "x.dart", "--root", str(tmp_path))
    f = tmp_path / ".sauces/state.json"
    assert f.read_text().endswith("\n")
    r = run_script("check_json.py", SCHEMA, str(f))
    assert r.returncode == 0, r.stdout + r.stderr


def test_hash_stable_across_move_and_sensitive_to_content(tmp_path):
    d = tmp_path / "one" / "designs"
    (d / "sub").mkdir(parents=True)
    (d / "a.png").write_bytes(b"aaa")
    (d / "sub" / "b.txt").write_bytes(b"bbb")
    (d / ".DS_Store").write_bytes(b"junk")
    h1 = run_script("sauces_state.py", "hash", str(d)).stdout.strip()
    assert len(h1) == 64
    (d / ".sauces").mkdir()
    (d / ".sauces" / "x").write_bytes(b"ignored")
    moved = tmp_path / "two" / "designs"
    moved.parent.mkdir()
    shutil.move(str(d), str(moved))
    assert run_script("sauces_state.py", "hash", str(moved)).stdout.strip() == h1
    (moved / "a.png").write_bytes(b"changed")
    assert run_script("sauces_state.py", "hash", str(moved)).stdout.strip() != h1


def test_hash_missing_path_exits_2(tmp_path):
    r = run_script("sauces_state.py", "hash", str(tmp_path / "nope"))
    assert r.returncode == 2
    assert r.stderr.strip()
