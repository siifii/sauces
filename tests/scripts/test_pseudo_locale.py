import json

import pytest

from conftest import run_script


def pseudo(tmp_path, name, text, *extra):
    src = tmp_path / name
    src.write_text(text, encoding="utf-8")
    out = tmp_path / ("out-" + name)
    r = run_script("pseudo_locale.py", str(src), "--out", str(out), *extra)
    assert r.returncode == 0, r.stdout + r.stderr
    return out.read_text(encoding="utf-8")


def test_json_flat_and_nested_keep_placeholders(tmp_path):
    data = {"title": "Welcome back", "home": {"greeting": "Hello, {name}", "i18next": "Hi {{name}}"},
            "count": 3}
    out = json.loads(pseudo(tmp_path, "en.json", json.dumps(data)))
    assert out["count"] == 3
    title = out["title"]
    assert title.startswith("[") and title.endswith("]")
    assert "Welcome" not in title and len(title) >= len("Welcome back") * 1.3
    assert "{name}" in out["home"]["greeting"] and "{{name}}" in out["home"]["i18next"]
    assert "Hello" not in out["home"]["greeting"]


def test_icu_plural_keeps_syntax_and_transforms_branches(tmp_path):
    msg = "{count, plural, one {# open order} other {# open orders}}"
    out = json.loads(pseudo(tmp_path, "en.json", json.dumps({"k": msg})))["k"]
    assert out.startswith("[{count, plural, one {") and "# " in out and "} other {" in out
    assert "order" not in out


def test_arb_skips_metadata_and_keeps_locale(tmp_path):
    arb = {"@@locale": "en", "loginTitle": "Welcome back",
           "@loginTitle": {"description": "Title on the login screen"},
           "loginWelcome": "Welcome, {name}", "@loginWelcome": {"placeholders": {"name": {}}}}
    out = json.loads(pseudo(tmp_path, "app_en.arb", json.dumps(arb), "--locale", "en_XA"))
    assert out["@@locale"] == "en_XA"
    assert out["@loginTitle"] == arb["@loginTitle"]
    assert "{name}" in out["loginWelcome"] and "Welcome" not in out["loginWelcome"]


def test_android_strings_xml(tmp_path):
    xml = ('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
           '  <string name="app_name" translatable="false">Sauces</string>\n'
           '  <string name="sign_in">Sign in</string>\n'
           '  <string name="welcome">Welcome, %1$s &amp; friends\\n</string>\n'
           '  <plurals name="orders"><item quantity="one">%d order</item>'
           '<item quantity="other">%d orders</item></plurals>\n</resources>\n')
    out = pseudo(tmp_path, "strings.xml", xml)
    assert ">Sauces</string>" in out
    assert "Sign in" not in out and "%1$s" in out and "&amp;" in out and "\\n" in out
    assert "%d" in out and "%d orders" not in out and "%d order<" not in out


def test_printf_and_swift_placeholders(tmp_path):
    out = json.loads(pseudo(tmp_path, "en.json", json.dumps({"a": "%@ has %d items, %s left"})))["a"]
    for ph in ("%@", "%d", "%s"):
        assert ph in out


def test_unknown_format_is_usage_error(tmp_path):
    src = tmp_path / "x.txt"
    src.write_text("hi")
    r = run_script("pseudo_locale.py", str(src), "--out", str(tmp_path / "o.txt"))
    assert r.returncode == 2


@pytest.mark.parametrize("flag", ["--help"])
def test_help(flag):
    assert run_script("pseudo_locale.py", flag).returncode == 0
