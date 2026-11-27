import json

from conftest import run_script


def check(tmp_path, name, source, target, *extra):
    s = tmp_path / ("src-" + name)
    t = tmp_path / ("tgt-" + name)
    s.write_text(source, encoding="utf-8")
    t.write_text(target, encoding="utf-8")
    r = run_script("i18n_check.py", str(s), str(t), *extra)
    return r, json.loads(r.stdout) if r.stdout.strip() else None


def test_json_matching_placeholders_pass(tmp_path):
    r, out = check(tmp_path, "en.json",
                   json.dumps({"a": "Hello, {name}", "b": {"c": "{count, plural, one {# order} other {# orders}}"}}),
                   json.dumps({"a": "مرحبًا، {name}", "b": {"c": "{count, plural, one {طلب #} other {# طلبات}}"}}))
    assert r.returncode == 0, r.stdout + r.stderr
    assert out["problems"] == []


def test_json_missing_and_renamed_placeholders_fail(tmp_path):
    r, out = check(tmp_path, "en.json", json.dumps({"a": "Hello, {name}", "b": "Hi {{user}}"}),
                   json.dumps({"a": "مرحبًا", "b": "أهلا {{usr}}"}))
    assert r.returncode == 1
    keys = sorted(p["key"] for p in out["problems"])
    assert keys == ["a", "b"]


def test_icu_plural_must_keep_other_and_variable(tmp_path):
    r, out = check(tmp_path, "en.json",
                   json.dumps({"k": "{count, plural, one {# order} other {# orders}}"}),
                   json.dumps({"k": "{n, plural, one {# طلب}}"}))
    assert r.returncode == 1 and out["problems"][0]["key"] == "k"


def test_arb_ignores_metadata(tmp_path):
    r, out = check(tmp_path, "app.arb",
                   json.dumps({"@@locale": "en", "w": "Welcome, {name}", "@w": {"description": "x"}}),
                   json.dumps({"@@locale": "ar", "w": "أهلا {name}", "@w": {"description": "y"}}))
    assert r.returncode == 0, out


def test_android_xml_printf(tmp_path):
    src = '<resources><string name="w">Welcome, %1$s (%2$d)</string></resources>'
    good = '<resources><string name="w">أهلا %1$s (%2$d)</string></resources>'
    bad = '<resources><string name="w">أهلا %s</string></resources>'
    assert check(tmp_path, "strings.xml", src, good)[0].returncode == 0
    r, out = check(tmp_path, "strings.xml", src, bad)
    assert r.returncode == 1 and out["problems"][0]["key"] == "w"


def test_keys_missing_in_target_are_listed_not_failed(tmp_path):
    r, out = check(tmp_path, "en.json", json.dumps({"a": "A", "b": "B"}), json.dumps({"a": "أ"}))
    assert r.returncode == 0 and out["missing"] == ["b"]


def test_help():
    assert run_script("i18n_check.py", "--help").returncode == 0


def test_plural_category_keys_may_drop_count_except_other(tmp_path):
    src = json.dumps({"o.one": "{count} order", "o.other": "{count} orders", "i_one": "{{count}} item",
                      "i_other": "{{count}} items"})
    ok = json.dumps({"o.one": "طلب واحد", "o.other": "{count} طلب", "i_one": "عنصر واحد",
                     "i_other": "{{count}} عنصر"})
    assert check(tmp_path, "en.json", src, ok)[0].returncode == 0
    bad = json.dumps({"o.one": "طلب واحد", "o.other": "طلبات", "i_one": "عنصر", "i_other": "عناصر"})
    r, out = check(tmp_path, "en.json", src, bad)
    assert r.returncode == 1 and sorted(p["key"] for p in out["problems"]) == ["i_other", "o.other"]
