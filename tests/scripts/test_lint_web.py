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
    ("a.tsx", 'const c = clsx("ml-2", active && "pr-4");',
     [(1, "physical-direction"), (1, "physical-direction")]),
    ("a.tsx", 'const buttonClass = "pl-4 rounded";', [(1, "physical-direction")]),
    ("a.tsx", 'const b = cva("px-4", { variants: { s: { lg: "mr-2" } } });', [(1, "physical-direction")]),
    ("a.tsx", "<div className={`ml-2 ${x}`} />", [(1, "physical-direction")]),
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
    ("a.tsx", 'const s = "Swipe left-to-right";'),
    ("a.tsx", 'const label = t("align.text-left");'),
    ("a.tsx", 'const url = "/docs/right-to-left";'),
    ("a.tsx", "<label htmlFor={id}>{label}</label>\n<div>\n<span />\n<input\n  id={id}\n/>"),
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


# ---------------------------------------------------------------- web-html

@pytest.mark.parametrize("rel,code,expected", [
    ("index.html", "<h1>Welcome back</h1>", [(1, "hardcoded-string")]),
    ("index.html", '<input placeholder="Email" data-i18n-attr="aria-label:login.email">',
     [(1, "hardcoded-string"), (1, "a11y-basic")]),
    ("index.html", '<p style="color: red">{x}</p>', [(1, "inline-style")]),
    ("index.html", "<main>\n<section>\n<h1 data-i18n=\"t\">Hi</h1>\n</main>", [(2, "html-parse")]),
    ("index.html", '<img src="logo.svg">', [(1, "a11y-basic")]),
    ("index.html", '<div onclick="go()" data-i18n="k">Go</div>', [(1, "a11y-basic")]),
    ("css/site.css", ".x { padding-right: 2px; color: #B3261E; }",
     [(1, "hardcoded-color"), (1, "physical-direction")]),
    ("components/x-card/x-card.js", "this.innerHTML = `\n  <h2>Card title</h2>`;",
     [(2, "hardcoded-string")]),
    ("components/x-card/x-card.js", "el.style.color = '#fff';", [(1, "hardcoded-color")]),
])
def test_web_html_hits(tmp_path, rel, code, expected):
    r = lint(tmp_path, rel, code, platform="web-html")
    assert r.returncode == 1, r.stderr
    assert sorted(rules(r)) == sorted(expected)


@pytest.mark.parametrize("rel,code", [
    ("index.html", '<h1 data-i18n="login.title">Welcome back</h1>'),
    ("index.html", '<p data-i18n="k">Hi <b>there</b></p>'),
    ("index.html", '<input id="e" placeholder="Email" data-i18n-attr="placeholder:login.email">\n'
                   '<label for="e" data-i18n="login.email">Email</label>'),
    ("index.html", '<label data-i18n="l">Email <input type="email"></label>'),
    ("index.html", "<ul><li data-i18n=\"a\">A<li data-i18n=\"b\">B</ul>"),
    ("index.html", "<p>&nbsp;&copy; 2026</p>"),
    ("index.html", "<script>const s = 'Sign in';</script><style>.x{color:var(--c)}</style>"),
    ("index.html", "<!-- <h1>Old</h1> -->"),
    ("page.njk", "<h1>{{ t('login.title') }}</h1>"),
    ("Card.astro", "---\nconst { title } = Astro.props;\n---\n<h2>{title}</h2>"),
    ("index.html", '<img src="d.svg" alt="">'),
])
def test_web_html_near_misses(tmp_path, rel, code):
    r = lint(tmp_path, rel, code, platform="web-html")
    assert r.returncode == 0, r.stdout + r.stderr
    assert findings(r) == []


def test_web_html_ignore_marker(tmp_path):
    r = lint(tmp_path, "index.html", "<h1>Brand</h1> <!-- sauces-lint-ignore -->",
             platform="web-html")
    assert r.returncode == 0, r.stdout


def test_web_html_js_template_line_offset(tmp_path):
    code = "const a = 1;\nconst b = 2;\nel.innerHTML = `<h2>Card title</h2>`;\n"
    r = lint(tmp_path, "x.js", code, platform="web-html")
    assert rules(r) == [(3, "hardcoded-string")]
