"""Web platforms (web-react, web-html): schemas, references, fixtures and wiring."""

import copy
import re
import json

import pytest

from conftest import REPO, fixture_copy, needs_claude, run_script, run_skill

WEB = ["web-react", "web-html"]
SAMPLE = REPO / "tests/data/sauces_sample"
MANIFEST_SCHEMA = "skills/ingest/references/manifest-schema.json"
PLAN_SCHEMA = "skills/plan/references/plan-schema.json"


def check(schema, data, tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps(data))
    return run_script("check_json.py", str(REPO / schema), str(path))


@pytest.mark.parametrize("platform", WEB)
def test_web_platform_in_enums(platform):
    for skill, schema in (
        ("scan-project", "profile-schema.json"),
        ("plan", "plan-schema.json"),
        ("verify", "summary-schema.json"),
    ):
        properties = json.loads((REPO / "skills" / skill / "references" / schema).read_text())["properties"]
        if skill == "scan-project":
            properties = properties["projects"]["items"]["properties"]
        assert platform in properties["platform"]["enum"], (skill, platform)


def test_platform_order_in_enums():
    order = ["flutter", "ios-swiftui", "android-compose", "kmp-cmp", "react-native",
             "web-react", "web-html"]
    for skill, schema in (("plan", "plan-schema.json"), ("verify", "summary-schema.json"),
                          ("scan-project", "profile-schema.json")):
        properties = json.loads((REPO / "skills" / skill / "references" / schema).read_text())["properties"]
        if skill == "scan-project":
            properties = properties["projects"]["items"]["properties"]
        assert properties["platform"]["enum"] == order, skill


def test_manifest_accepts_breakpoint_screens(tmp_path):
    manifest = json.loads((SAMPLE / "manifest.json").read_text())
    r = check(MANIFEST_SCHEMA, manifest, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    web = copy.deepcopy(manifest)
    web["sources"][0]["viewport"] = {"width": 1440, "dpr": 1}
    screen = web["screens"][0]
    screen.update({"id": "login@1440", "base": "login", "breakpoint": 1440})
    r = check(MANIFEST_SCHEMA, web, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    web["sources"][0]["viewport"] = {"width": "wide", "dpr": 1}
    assert check(MANIFEST_SCHEMA, web, tmp_path).returncode == 1


def test_web_plan_requires_breakpoints(tmp_path):
    plan = json.loads((SAMPLE / "plan.json").read_text())
    assert check(PLAN_SCHEMA, plan, tmp_path).returncode == 0
    web = dict(plan, platform="web-react")
    r = check(PLAN_SCHEMA, web, tmp_path)
    assert r.returncode == 1 and "breakpoints" in r.stdout, r.stdout + r.stderr
    web["breakpoints"] = [{"name": "desktop", "min_width": 1024, "source": "design"}]
    r = check(PLAN_SCHEMA, web, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    web["breakpoints"][0]["source"] = "guess"
    assert check(PLAN_SCHEMA, web, tmp_path).returncode == 1


def test_ingest_breakpoint_reference():
    text = (REPO / "skills/ingest/references/breakpoints.md").read_text()
    for needle in ("viewport", "@", "narrowest", "web-react", "web-html", "not duplicates"):
        assert needle in text
    assert "references/breakpoints.md" in (REPO / "skills/ingest/SKILL.md").read_text()


def test_plan_skill_lists_web_and_breakpoints():
    text = (REPO / "skills/plan/SKILL.md").read_text()
    assert "web-react" in text and "web-html" in text and "breakpoints" in text


def lint_platform(platform, *paths):
    r = run_script("lint_generated.py", "--platform", platform, *map(str, paths))
    return [(f["file"].rsplit("/", 1)[-1], f["rule"]) for f in json.loads(r.stdout)["findings"]]


@pytest.mark.parametrize("name,files", [
    ("web-react-vite", ["src/components/Button/Button.tsx", "src/theme/tokens.css",
                        "src/i18n/locales/ar.json", "package-lock.json"]),
    ("web-react-next", ["app/[locale]/page.tsx", "app/globals.css",
                        "messages/ar.json", "package-lock.json"]),
])
def test_react_fixture_layout(name, files):
    root = REPO / "examples/targets" / name
    for f in files:
        assert (root / f).is_file(), f
    for build_dir in ("node_modules", ".next", "dist"):
        assert not (root / build_dir).exists(), build_dir


def test_react_fixture_gaps_are_lint_findings():
    vite = REPO / "examples/targets/web-react-vite/src/components/Card/Card.module.css"
    assert sorted(lint_platform("web-react", vite)) == [
        ("Card.module.css", "hardcoded-color"), ("Card.module.css", "physical-direction")]
    nxt = REPO / "examples/targets/web-react-next/components/Card.tsx"
    assert lint_platform("web-react", nxt) == [("Card.tsx", "physical-direction")]


@pytest.mark.parametrize("name,src", [("web-react-vite", "src"), ("web-react-next", "components")])
def test_react_fixture_other_sources_lint_clean(name, src):
    root = REPO / "examples/targets" / name
    files = [p for p in (root / src).rglob("*") if p.suffix in (".tsx", ".ts", ".css")
             and p.name not in ("Card.module.css", "Card.tsx", "tokens.css")
             and ".test." not in p.name]
    assert files
    assert lint_platform("web-react", *files) == []


WEB_HTML = REPO / "examples/targets/web-html"


def test_web_html_fixture_layout():
    for f in ("index.html", "css/tokens.css", "css/base.css", "components/x-button/x-button.js",
              "components/x-button/x-button.css", "components/x-card/x-card.js",
              "components/x-card/x-card.css", "i18n.js", "locales/en.json", "locales/ar.json",
              "icons.svg", "README.md"):
        assert (WEB_HTML / f).is_file(), f
    assert not (WEB_HTML / "package.json").exists()
    assert not (WEB_HTML / "node_modules").exists()
    i18n = (WEB_HTML / "i18n.js").read_text()
    for needle in ("export async function setLocale", "Intl.PluralRules", "data-i18n-attr",
                   "lang", "dir"):
        assert needle in i18n


def test_web_html_fixture_is_lint_clean_except_gap():
    files = sorted(p for p in WEB_HTML.rglob("*") if p.suffix in (".html", ".css", ".js"))
    r = run_script("lint_generated.py", "--platform", "web-html",
                   "--allow-colors", "**/css/tokens.css", *map(str, files))
    found = [(f["file"].split("examples/targets/web-html/")[-1], f["rule"])
             for f in json.loads(r.stdout)["findings"]]
    assert found == [("components/x-card/x-card.css", "physical-direction")]


def test_web_html_locales_match():
    en = json.loads((WEB_HTML / "locales/en.json").read_text())
    ar = json.loads((WEB_HTML / "locales/ar.json").read_text())
    base = lambda d: {k.split(".")[0] if k.endswith((".one", ".other", ".zero", ".two", ".few", ".many")) else k for k in d}
    assert base(en) == base(ar)


def test_scan_web_detection_rules():
    skill = (REPO / "skills/scan-project/SKILL.md").read_text()
    assert "| `web-react` |" in skill and "| `web-html` |" in skill
    assert "`react-native`, `web-react`, `web-html`" in skill
    react = (REPO / "skills/scan-project/references/web-react.md").read_text()
    for needle in ("react-dom", "next", "vite", "App Router", "Pages Router", "@theme",
                   "CSS Modules", "next-intl", "react-i18next", "without executing"):
        assert needle in react, needle
    # Review Focus 1: RN wins over web-react
    assert "react-native" in react and "never `web-react`" in react
    html = (REPO / "skills/scan-project/references/web-html.md").read_text()
    for needle in ("Eleventy", "Astro", "custom elements", "data-i18n", "Django", "Rails",
                   "PHP", "WordPress", "unsupported"):
        assert needle in html, needle


@needs_claude
@pytest.mark.skill
@pytest.mark.parametrize("name,platform", [("web-react-vite", "web-react"),
                                           ("web-react-next", "web-react"),
                                           ("web-html", "web-html")])
def test_scan_profiles_web_fixture(name, platform, tmp_path):
    workdir = fixture_copy(name, tmp_path)
    result = run_skill(workdir, "/sauces:scan-project")
    path = workdir / ".sauces" / "project-profile.json"
    assert path.is_file(), result.stdout + result.stderr
    r = run_script("check_json.py", str(REPO / "skills/scan-project/references/profile-schema.json"),
                   str(path))
    assert r.returncode == 0, r.stdout
    project = json.loads(path.read_text())["projects"][0]
    assert project["platform"] == platform
    assert project["localization"]["rtl"] is True
    assert (workdir / project["root"] / project["theme"]["tokens_source"]).exists()


SECTIONS = ["## Tokens", "## Components", "## Responsive", "## Previews and tests", "## Strings",
            "## Assets", "## State", "## Folders", "## Checks", "## Don't"]


@pytest.mark.parametrize("platform,needles", [
    ("web-react", ["'use client'", "server-compatible", "ms-*", "@theme", "next/image",
                   "TODO(sauces)", "--platform web-react", "never invent a translation"]),
    ("web-html", ["light DOM", "data-i18n-attr", "Intl.PluralRules", "<use href",
                  "no build step", "--platform web-html", "Eleventy", "Astro"]),
])
def test_build_reference(platform, needles):
    text = (REPO / f"skills/build/references/{platform}.md").read_text()
    assert [s for s in SECTIONS if s in text] == SECTIONS
    for n in needles:
        assert n in text, n
    assert len(text.split()) < 900


def test_web_capture_reference():
    text = (REPO / "skills/verify/references/web-capture.md").read_text()
    for needle in ("@playwright/test", "npx -y", "playwright@1.61.1", "python3 -m http.server",
                   "deviceScaleFactor", "reducedMotion", "document.fonts.ready",
                   "clip", "full.png", "10%", "Storybook", "manual checklist",
                   "150 MB", "eval-approve", "narrowest", "not designed, not verified",
                   "Tab", "notFound()", "rollupOptions", ".sauces/verify/fixtures/",
                   "package.json", "```js"):
        assert needle in text, needle
    for p in ("web-react", "web-html"):
        ref = (REPO / f"skills/verify/references/{p}.md").read_text()
        assert "web-capture.md" in ref
        assert "## Render test" in ref and "## Run" in ref
    skill = (REPO / "skills/verify/SKILL.md").read_text()
    assert "web-capture.md" in skill and "not designed, not verified" in skill


def test_playwright_pin_matches_tests():
    text = (REPO / "skills/verify/references/web-capture.md").read_text()
    fixtures = (REPO / "tests/fixtures/test_web_fixtures.py").read_text()
    pin = re.search(r"playwright@(\d+\.\d+\.\d+)", text).group(1)
    assert f'PLAYWRIGHT = "playwright@{pin}"' in fixtures


def test_scaffold_routes_web():
    skill = (REPO / "skills/scaffold/SKILL.md").read_text()
    for needle in ("`react`", "`html`", "--next", "web-app/", "web-html/",
                   "react → web-react → web-app/", "html → web-html → web-html/"):
        assert needle in skill, needle
    react = (REPO / "skills/scaffold/references/web-react.md").read_text()
    for needle in ("npm create vite@latest web-app", "react-ts", "react-i18next",
                   "create-next-app", "next-intl", "CSS Modules", "--help", "README"):
        assert needle in react, needle
    html = (REPO / "skills/scaffold/references/web-html.md").read_text()
    for needle in ("index.html", "css/tokens.css", "i18n.js", "icons.svg", "no build step",
                   "README", "package.json"):
        assert needle in html, needle


def test_report_has_breakpoints_line():
    text = (REPO / "skills/report/SKILL.md").read_text()
    assert "Breakpoints" in text and "not designed, not verified" in text


def test_summary_accepts_breakpoint_ids(tmp_path):
    summary = json.loads((SAMPLE / "verify/summary.json").read_text())
    summary["platform"] = "web-react"
    for r in summary["results"]:
        r["id"] = r["id"].replace("login--", "login@1440--")
        r["screen"] = "login@1440"
    r = check("skills/verify/references/summary-schema.json", summary, tmp_path)
    assert r.returncode == 0, r.stdout
    summary["results"][0]["id"] = "login@--default"
    assert check("skills/verify/references/summary-schema.json", summary, tmp_path).returncode == 1


def test_pseudo_locale_reference_covers_every_platform():
    text = (REPO / "skills/verify/references/pseudo-locale.md").read_text()
    for platform in ("web-react", "web-html", "react-native", "flutter", "android-compose",
                     "kmp-cmp", "ios-swiftui"):
        assert f"**{platform}" in text or f"/ {platform}" in text, platform
    assert "pseudo_locale.py" in text and "pseudo_issues" in text
    assert "pseudo-locale.md" in (REPO / "skills/verify/SKILL.md").read_text()


def test_translate_skill_contract():
    text = (REPO / "skills/translate/SKILL.md").read_text()
    assert text.startswith("---\nname: translate\n")
    for needle in ("/sauces:translate", "i18n_check.py", "needs_review", "x-sauces-review",
                   "translatable=\"false\"", "eval-approve", "translations.json", "todos.json",
                   "zero, one, two, few, many, other"):
        assert needle in text, needle
    assert len(text.split()) < 2000
    assert "/sauces:translate" in (REPO / "README.md").read_text()


def test_lite_mode_is_wired_through_cook_ingest_verify():
    cook = (REPO / "skills/cook/SKILL.md").read_text()
    assert "--lite" in cook and ".sauces/lite" in cook
    verify = (REPO / "skills/verify/SKILL.md").read_text()
    assert ".sauces/lite" in verify and '"lite": true' in verify
    assert ".sauces/lite" in (REPO / "skills/ingest/references/breakpoints.md").read_text()
    assert "--lite" in (REPO / "README.md").read_text()
