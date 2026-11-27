"""Figma variables to tokens: schema, references, report."""
import copy
import json

from conftest import REPO, run_script

SAMPLE = REPO / "tests/data/sauces_sample"
TOKENS = REPO / "tests/data/figma_tokens.json"
SCHEMA = REPO / "skills/ingest/references/manifest-schema.json"


def manifest_with(tokens, tmp_path):
    manifest = json.loads((SAMPLE / "manifest.json").read_text())
    manifest["tokens"] = tokens
    path = tmp_path / "m.json"
    path.write_text(json.dumps(manifest))
    return path


def check(path):
    return run_script("check_json.py", str(SCHEMA), str(path)).returncode


def read(rel):
    return (REPO / rel).read_text()


def test_references_describe_figma_tokens():
    figma = read("skills/ingest/references/figma.md")
    for needle in ("alias_of", "modes.dark", "source.kind", "style", "never snap", "Never invent"):
        assert needle in figma, needle
    matching = read("skills/plan/references/matching.md")
    for needle in ("Figma token name", "source.name", "recommendation"):
        assert needle in matching, needle
    assert "figma.md" in read("skills/ingest/SKILL.md")
    assert "modes.dark" in read("skills/plan/references/dark-mode.md")


def test_schema_accepts_figma_tokens(tmp_path):
    assert check(manifest_with(json.loads(TOKENS.read_text()), tmp_path)) == 0


def test_schema_rejects_bad_source_and_modes(tmp_path):
    base = json.loads(TOKENS.read_text())
    bad = copy.deepcopy(base)
    bad["colors"][0]["source"]["kind"] = "figma-api"
    assert check(manifest_with(bad, tmp_path)) == 1
    bad = copy.deepcopy(base)
    bad["colors"][0]["modes"]["dark"] = "blue"
    assert check(manifest_with(bad, tmp_path)) == 1
    bad = copy.deepcopy(base)
    bad["spacing"][1]["origin"] = "guess"
    assert check(manifest_with(bad, tmp_path)) == 1
