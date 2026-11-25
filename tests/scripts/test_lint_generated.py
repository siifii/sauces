import json

import pytest

from conftest import run_script


def lint(tmp_path, rel, code, *extra, platform="flutter"):
    f = tmp_path / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(code)
    return run_script("lint_generated.py", "--platform", platform, *extra, str(f))


def findings(r):
    return json.loads(r.stdout)["findings"]


def rules(r):
    return [(f["line"], f["rule"]) for f in findings(r)]


def test_flags_hex_color(tmp_path):
    r = lint(tmp_path, "lib/a.dart", "final c = Color(0xFF3D5AFE);\n")
    assert r.returncode == 1
    assert rules(r) == [(1, "hardcoded-color")]
    out = json.loads(r.stdout)
    assert out["version"] == 1
    assert findings(r)[0]["text"] == "final c = Color(0xFF3D5AFE);"
    assert findings(r)[0]["file"].endswith("lib/a.dart")


@pytest.mark.parametrize("snippet", [
    "Color.fromARGB(255, 1, 2, 3)", "Color.fromRGBO(1, 2, 3, 1)", "Colors.red", "Colors.white70",
])
def test_flags_other_colors(tmp_path, snippet):
    r = lint(tmp_path, "lib/a.dart", f"final c = {snippet};\n")
    assert rules(r) == [(1, "hardcoded-color")]


def test_transparent_allowed(tmp_path):
    r = lint(tmp_path, "lib/a.dart", "final c = Colors.transparent;\n")
    assert r.returncode == 0 and findings(r) == []


def test_flags_text_literal(tmp_path):
    r = lint(tmp_path, "lib/a.dart", "Widget w = Text('Sign in');\n")
    assert r.returncode == 1
    assert rules(r) == [(1, "hardcoded-string")]


@pytest.mark.parametrize("code", [
    'const Text("Sign in")', "SelectableText('x')", "Text(r'raw')", "Text('Hi $name')",
    "Text('Hi ${user.name}')", "Text(\n  'Sign in',\n)", "Text(  \n\n 'a')",
    "Text('''multi\nline''')", "InputDecoration(hintText: 'Email')",
    "InputDecoration(labelText: \"Email\")", "x(helperText: 'a')", "x(errorText: 'a')",
    "IconButton(tooltip: 'Back')", "x(semanticsLabel: 'a')", "Text('a ${b ? 'x' : 'y'} c')",
])
def test_flags_string_forms(tmp_path, code):
    r = lint(tmp_path, "lib/a.dart", f"final w = {code};\n")
    assert [x[1] for x in rules(r)] == ["hardcoded-string"]


def test_multiline_reports_start_line(tmp_path):
    r = lint(tmp_path, "lib/a.dart", "a;\nText(\n  'Sign in',\n);\n")
    assert rules(r) == [(2, "hardcoded-string")]


def test_allows_l10n_lookup(tmp_path):
    r = lint(tmp_path, "lib/a.dart", "Widget w = Text(context.l10n.signIn);\n")
    assert r.returncode == 0 and findings(r) == []


def test_empty_string_allowed(tmp_path):
    r = lint(tmp_path, "lib/a.dart", "a = Text('');\nb = Text(\"\");\nc = x(hintText: '');\n")
    assert r.returncode == 0


def test_non_literal_args_allowed(tmp_path):
    r = lint(tmp_path, "lib/a.dart", "a = Text(title, style: s);\nb = MyText('x');\nc = Text.rich(x);\n")
    assert r.returncode == 0


def test_allows_theme_folder(tmp_path):
    r = lint(tmp_path, "lib/theme/colors.dart", "const c = Color(0xFF3D5AFE);\nconst d = Colors.red;\n")
    assert r.returncode == 0 and findings(r) == []


def test_allows_strings_class(tmp_path):
    r = lint(tmp_path, "lib/login/login_strings.dart", "final t = Text('Sign in');\n")
    assert r.returncode == 0


def test_allows_l10n_and_generated(tmp_path):
    assert lint(tmp_path, "lib/l10n/app_en.dart", "x = Text('a');\n").returncode == 0
    assert lint(tmp_path, "lib/a.g.dart", "x = Text('a');\n").returncode == 0


def test_allow_glob_added_to_defaults(tmp_path):
    r = lint(tmp_path, "lib/gen/x.dart", "x = Text('a');\n", "--allow", "**/gen/**")
    assert r.returncode == 0
    r = lint(tmp_path, "lib/theme/x.dart", "x = Text('a');\n", "--allow", "**/gen/**")
    assert r.returncode == 0  # default still applies
    r = lint(tmp_path, "lib/other/x.dart", "x = Text('a');\n", "--allow", "**/gen/**")
    assert r.returncode == 1


def test_glob_zero_directories(tmp_path, monkeypatch):
    f = tmp_path / "theme" / "x.dart"
    f.parent.mkdir()
    f.write_text("x = Colors.red;\n")
    monkeypatch.chdir(tmp_path)
    from conftest import REPO
    import subprocess, sys
    r = subprocess.run([sys.executable, "-I", str(REPO / "scripts/lint_generated.py"),
                        "--platform", "flutter", "theme/x.dart"],
                       capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stdout


def test_ignore_comment(tmp_path):
    code = "a = Text('x'); // sauces-lint-ignore\nb = Text('y');\n"
    r = lint(tmp_path, "lib/a.dart", code)
    assert rules(r) == [(2, "hardcoded-string")]


def test_commented_code_not_flagged(tmp_path):
    code = "// Text('x'); Colors.red\n/* Text('y');\n Color(0xFF000000) */\nfinal ok = 1;\n"
    r = lint(tmp_path, "lib/a.dart", code)
    assert r.returncode == 0


def test_comment_markers_inside_strings(tmp_path):
    code = "final u = 'http://x.y'; final c = Colors.red;\nfinal t = Text('a // b');\n"
    r = lint(tmp_path, "lib/a.dart", code)
    assert rules(r) == [(1, "hardcoded-color"), (2, "hardcoded-string")]


def test_block_comment_keeps_line_numbers(tmp_path):
    code = "/* a\nb\nc */ final c = Colors.red;\n"
    assert rules(lint(tmp_path, "lib/a.dart", code)) == [(3, "hardcoded-color")]


def test_ordering_and_non_dart_skipped(tmp_path):
    b = tmp_path / "lib" / "b.dart"
    a = tmp_path / "lib" / "a.dart"
    n = tmp_path / "lib" / "n.txt"
    b.parent.mkdir()
    b.write_text("x = Colors.red;\n")
    a.write_text("x = Text('a');\ny = Colors.red;\n")
    n.write_text("Colors.red\n")
    r = run_script("lint_generated.py", "--platform", "flutter", str(b), str(n), str(a))
    fs = findings(r)
    assert [(f["file"].split("/")[-1], f["line"]) for f in fs] == [("a.dart", 1), ("a.dart", 2), ("b.dart", 1)]


def test_no_files(tmp_path):
    r = run_script("lint_generated.py", "--platform", "flutter")
    assert r.returncode == 0
    assert json.loads(r.stdout) == {"version": 1, "findings": []}


def test_missing_file(tmp_path):
    r = run_script("lint_generated.py", "--platform", "flutter", str(tmp_path / "nope.dart"))
    assert r.returncode == 2
    assert "file not found:" in r.stderr and "nope.dart" in r.stderr


def test_unknown_platform(tmp_path):
    r = lint(tmp_path, "lib/a.dart", "x\n", platform="cobol")
    assert r.returncode == 2


def test_text_truncated(tmp_path):
    r = lint(tmp_path, "lib/a.dart", "x = Colors.red; // " + "z" * 400 + "\n")
    assert len(findings(r)[0]["text"]) == 200


@pytest.mark.parametrize("code", ["Text('')", "Text(\"\")", "Text(\'\'\'\'\'\')", 'Text("""""")',
                                  "Text(r'')", 'Text(r"")', "Text(cond ? '' : l10n.a)"])
def test_empty_forms_allowed(tmp_path, code):
    assert lint(tmp_path, "lib/a.dart", f"final w = {code};\n").returncode == 0


def test_flags_ternary_both_branches(tmp_path):
    r = lint(tmp_path, "lib/a.dart", "final w = Text(cond ? 'a' : 'b');\n")
    assert rules(r) == [(1, "hardcoded-string")] * 2


def test_flags_ternary_one_branch_and_multiline(tmp_path):
    r = lint(tmp_path, "lib/a.dart", "final w = Text(\n  cond\n    ? l10n.a\n    : 'b',\n);\n")
    assert rules(r) == [(1, "hardcoded-string")]


def test_flags_null_coalescing(tmp_path):
    r = lint(tmp_path, "lib/a.dart", "final w = Text(x ?? 'dflt');\n")
    assert rules(r) == [(1, "hardcoded-string")]


def test_flags_named_arg_ternary(tmp_path):
    r = lint(tmp_path, "lib/a.dart", "final d = InputDecoration(hintText: isErr ? 'x' : null);\n")
    assert rules(r) == [(1, "hardcoded-string")]


def test_allows_l10n_ternary(tmp_path):
    r = lint(tmp_path, "lib/a.dart",
             "final w = Text(cond ? l10n.a : l10n.b);\nfinal v = Text(x ?? l10n.c, style: s);\n")
    assert r.returncode == 0


def test_literal_in_later_argument_not_flagged(tmp_path):
    r = lint(tmp_path, "lib/a.dart", "final w = Text(title, semantics: foo(a: 'k'), key: Key('k'));\n")
    assert r.returncode == 0


@pytest.mark.parametrize("code", ["Text('$name')", "Text('${l10n.count}')", 'Text("${n}")',
                                  "Text(cond ? '$a' : l10n.b)"])
def test_interpolation_only_allowed(tmp_path, code):
    assert lint(tmp_path, "lib/a.dart", f"final w = {code};\n").returncode == 0


@pytest.mark.parametrize("code", ["Text('Hi $name')", "Text('${n} items')", "Text('$a$b')",
                                  "Text(r'$name')", "Text('$a!')"])
def test_text_around_interpolation_flagged(tmp_path, code):
    assert rules(lint(tmp_path, "lib/a.dart", f"final w = {code};\n")) == [(1, "hardcoded-string")]


def test_line_text_with_form_feed_stays_aligned(tmp_path):
    r = lint(tmp_path, "lib/a.dart", "a;\x0c\nb = Colors.red;\n")
    assert findings(r)[0]["text"] == "b = Colors.red;"


def test_allow_colors_skips_only_the_color_rule(tmp_path):
    code = "const brand = Color(0xFF3D5AFE);\nfinal w = Text('Hi');\n"
    r = lint(tmp_path, "lib/core/constants/app_colors.dart", code,
             "--allow-colors", "**/constants/app_colors.dart")
    assert r.returncode == 1
    assert rules(r) == [(2, "hardcoded-string")]  # strings still checked in token files
    r = lint(tmp_path, "lib/core/constants/app_colors.dart", code.split("\n")[0] + "\n",
             "--allow-colors", "**/constants/app_colors.dart")
    assert r.returncode == 0


def test_allow_colors_does_not_cover_other_files(tmp_path):
    r = lint(tmp_path, "lib/features/login/view/login_page.dart",
             "final c = Colors.red;\n", "--allow-colors", "**/constants/app_colors.dart")
    assert rules(r) == [(1, "hardcoded-color")]
