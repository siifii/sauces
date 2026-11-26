import json

import pytest

from conftest import run_script


def lint(tmp_path, rel, code, *extra, platform="web-react"):
    f = tmp_path / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(code)
    return run_script("lint_generated.py", "--platform", platform, *extra, str(f))


def findings(r):
    return json.loads(r.stdout)["findings"]


def rules(r):
    return [(f["line"], f["rule"]) for f in findings(r)]


# ---------------------------------------------------------------- web-react

@pytest.mark.parametrize("rel,code,expected", [
    ("a.tsx", 'const s = {color: "#3D5AFE"};', [(1, "hardcoded-color")]),
    ("a.tsx", "const B = styled.button`\n  background: rgb(61 90 254);\n`;", [(2, "hardcoded-color")]),
    ("a.tsx", '<div className="bg-[#3D5AFE] p-4" />', [(1, "hardcoded-color")]),
    ("a.module.css", ".x { color: #fff; }", [(1, "hardcoded-color")]),
    ("a.css", ".x {\n  color: oklch(0.6 0.2 260);\n}", [(2, "hardcoded-color")]),
    ("a.tsx", "<h1>Welcome back</h1>", [(1, "hardcoded-string")]),
    ("a.tsx", "<p>Hello <b>{name}</b></p>", [(1, "hardcoded-string")]),
    ("a.tsx", '<input aria-label="Email" id="e" />', [(1, "hardcoded-string")]),
    ("a.tsx", '<img src={eye} alt="Show password" />', [(1, "hardcoded-string")]),
    ("a.css", ".x { margin-left: 8px; }", [(1, "physical-direction")]),
    ("a.css", ".x { text-align: right; float: left; }",
     [(1, "physical-direction"), (1, "physical-direction")]),
    ("a.tsx", "const s = {paddingRight: 4};", [(1, "physical-direction")]),
    ("a.tsx", '<div className="ml-2 text-left" />',
     [(1, "physical-direction"), (1, "physical-direction")]),
    ("a.tsx", "<img src={logo} />", [(1, "a11y-basic")]),
    ("a.tsx", "<div onClick={go}>{t('k')}</div>", [(1, "a11y-basic")]),
    ("a.tsx", "<input type=\"email\" />", [(1, "a11y-basic")]),
])
def test_web_react_hits(tmp_path, rel, code, expected):
    r = lint(tmp_path, rel, code)
    assert r.returncode == 1, r.stderr
    assert sorted(rules(r)) == sorted(expected)


@pytest.mark.parametrize("rel,code", [
    ("a.css", "#fade { color: var(--brand); }"),
    ("a.css", "a:hover #add {\n  color: currentColor;\n}"),
    ("a.css", ".x { margin-inline-start: 8px; border-color: transparent; }"),
    ("a.tsx", 'const [v, setV] = useState<string>("");'),
    ("a.tsx", "<h1>{t('login.title')}</h1>"),
    ("a.tsx", '<img src={d} alt="" />'),
    ("a.tsx", '<div className="bg-primary ms-2 text-start" />'),
    ("a.tsx", "if (a > b && c < d) go();"),
    ("a.tsx", '<input id="email" />\n<label htmlFor="email">{t("e")}</label>'),
    ("a.tsx", "// <h1>Old title</h1>"),
])
def test_web_react_near_misses(tmp_path, rel, code):
    r = lint(tmp_path, rel, code)
    assert r.returncode == 0, r.stdout + r.stderr
    assert findings(r) == []


def test_web_react_token_file_allows_colors(tmp_path):
    code = ":root {\n  --brand: #3D5AFE;\n}\n"
    r = lint(tmp_path, "src/theme/tokens.css", code, "--allow-colors", "**/src/theme/**")
    assert r.returncode == 0, r.stdout
    r = lint(tmp_path, "src/theme/tokens.css", code + ".x { margin-left: 1px; }\n",
             "--allow-colors", "**/src/theme/**")
    assert rules(r) == [(4, "physical-direction")]
