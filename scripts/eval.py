#!/usr/bin/env python3
"""Score Sauces pipeline runs on the example fixtures (milestone evals).

Score mode (default) reads <results>/<fixture>/ for each fixture: the .sauces/
working state a `/sauces:cook` run left there, and the project's code. It prints
a markdown table:

  | fixture | mode | builds | rendered | lint | fidelity(default) | reuse decisions | todos | PASS |

  mode               create (scaffolded), follow (existing project) or the profile mode
  builds             --builds-cmd exits 0 in the project folder
  rendered           verify rendered every manifest screen state, once each
  lint               lint_generated.py is clean on generated and changed UI source
  fidelity(default)  verify score of the first screen's default state
  reuse decisions    plan items by decision (reuse / extend / new)
  todos              entries in .sauces/todos.json
  PASS               builds and rendered and lint and fidelity >= 90;
                     --run also requires cook to exit successfully

--run first copies each fixture from examples/targets/ to <results>/<fixture>/,
git-inits it, writes .sauces/eval-approve (no questions: the plan is
auto-approved, and cook deletes the file when it finishes) and runs
`claude -p "/sauces:cook <design>"` there with this plugin. That costs tokens,
needs network and takes a long time per fixture.

  lint uses the same allow globs as the build skill: theme/, l10n/, *_strings.dart
  by default, plus color literals in the tokens folder and theme.tokens_source.

Stdlib only. Exit codes: 0 every row passes, 1 a row fails, 2 usage error,
4 missing external tool (claude for --run).
"""
import argparse
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HEADER = ("| fixture | mode | builds | rendered | lint | fidelity(default) "
          "| reuse decisions | todos | PASS |")
RULE = "|---|---|---|---|---|---|---|---|---|"
PASS_SCORE = 90.0
SKIP_DIRS = {".dart_tool", "build", "gen", ".git", ".sauces", "node_modules", "Pods", ".expo", ".gradle", "DerivedData"}


def load(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


SOURCE_EXTENSIONS = {
    "flutter": {".dart"},
    "android-compose": {".kt"},
    "kmp-cmp": {".kt"},
    "ios-swiftui": {".swift"},
    "react-native": {".js", ".jsx", ".ts", ".tsx"},
}


def select_project(profile, plan):
    matches = [
        project for project in profile.get("projects", [])
        if project.get("platform") == plan.get("platform")
        and ("project_root" not in plan or project.get("root") == plan["project_root"])
    ]
    return matches[0] if len(matches) == 1 else {}


def source_files(root, project, entries, platform):
    """Find changed and generated UI files and surface missing recorded paths."""
    extensions = SOURCE_EXTENSIONS.get(platform, set())
    files, missing = set(), []
    for entry in entries:
        path = root / entry
        if not path.exists() and project is not None:
            path = project / entry
        if path.is_dir():
            for folder, dirs, names in os.walk(path):
                dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
                files.update(Path(folder) / name for name in names
                             if Path(name).suffix in extensions)
        elif path.is_file():
            if path.suffix in extensions:
                files.add(path)
        else:
            missing.append(entry)
    return sorted(str(file.relative_to(root)) for file in files), missing


def color_globs(root, profile):
    globs = ["**/tokens/**", "**/Tokens/**"]
    source = (profile.get("theme") or {}).get("tokens_source")
    if source:
        path = root / source
        if not path.exists():
            path = root / profile.get("root", ".") / source
        if path.exists() and path.resolve().is_relative_to(root.resolve()):
            relative = path.resolve().relative_to(root.resolve()).as_posix()
            globs.append(f"{relative}/**" if path.is_dir() else relative)
    return globs


def run_lint(root, files, allow_colors, platform):
    if not files:
        return True, "✓"
    flags = [arg for glob in allow_colors for arg in ("--allow-colors", glob)]
    r = subprocess.run(
        [sys.executable, "-I", str(REPO / "scripts" / "lint_generated.py"), "--platform", platform,
         *flags, *files],
        cwd=root, capture_output=True, text=True)
    if r.returncode == 0:
        return True, "✓"
    try:
        n = len(json.loads(r.stdout)["findings"])
    except (ValueError, KeyError):
        return False, "✗ error"
    return False, f"✗ {n}"


def run_builds(project, cmd):
    if project is None or not project.is_dir():
        return False
    try:
        r = subprocess.run(shlex.split(cmd), cwd=project, capture_output=True, text=True,
                           timeout=1800)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0


def score_fixture(root, name, builds_cmd, require_captures=False):
    sauces = root / ".sauces"
    if not sauces.is_dir():
        return [name, "not run", "–", "–", "–", "–", "–", "–", "FAIL"], False
    profile = load(sauces / "project-profile.json") or {}
    state = load(sauces / "state.json") or {}
    plan = load(sauces / "plan.json") or {}
    summary = load(sauces / "verify" / "summary.json") or {}
    todos = load(sauces / "todos.json")
    selected = select_project(profile, plan)
    platform = selected.get("platform")
    project = root / selected.get("root", ".") if selected else None
    generated = state.get("generated_files", [])
    changed = state.get("changed_files", [])

    if selected.get("root") in set(generated) - {"."}:
        mode = "create"
    elif profile.get("mode") == "existing":
        mode = "follow"
    else:
        mode = profile.get("mode", "–")

    command = builds_cmd
    if command is None and platform == "flutter":
        command = "flutter analyze --no-fatal-infos --no-fatal-warnings"
    builds = bool(command) and run_builds(project, command)
    results = summary.get("results", [])
    manifest = load(sauces / "manifest.json") or {}
    screens = manifest.get("screens", [])
    expected = {f"{s.get('id')}--{st.get('id')}"
                for s in screens for st in s.get("states", [])}
    ids = [r.get("id") for r in results]
    rendered = (bool(screens) and summary.get("platform") == platform
                and all(s.get("id") and s.get("states")
                        and all(st.get("id") for st in s["states"]) for s in screens)
                and bool(results) and all(r.get("rendered") for r in results)
                and len(ids) == len(set(ids)) and expected <= set(ids))
    if require_captures:
        rendered = rendered and all(
            has_capture(sauces, result, rtl=selected.get("localization", {}).get("rtl", False))
            and result.get("passed") is True and result.get("nondeterministic") is False
            for result in results
        )
    files, missing = source_files(root, project, generated + changed, platform)
    lint_ok, lint_cell = run_lint(root, files, color_globs(root, selected), platform)
    if missing:
        lint_ok, lint_cell = False, f"✗ {len(missing)} missing"

    default = next((r for r in results if r.get("state") == "default"), None)
    score = default.get("score") if default else None
    fidelity = f"{score:.1f}" if isinstance(score, (int, float)) else "–"

    counts = {}
    for item in plan.get("items", []):
        d = item.get("decision")
        if d in ("reuse", "extend", "new"):
            counts[d] = counts.get(d, 0) + 1
    reuse = " · ".join(f"{counts[d]} {d}" for d in ("reuse", "extend", "new") if d in counts) or "–"
    todo_count = str(len(todos)) if isinstance(todos, list) else "–"

    passed = (builds and rendered and lint_ok
              and isinstance(score, (int, float)) and score >= PASS_SCORE)
    mark = lambda ok: "✓" if ok else "✗"
    return [name, mode, mark(builds), mark(rendered), lint_cell, fidelity, reuse, todo_count,
            "PASS" if passed else "FAIL"], passed


def has_png(path):
    try:
        with path.open("rb") as stream:
            header = stream.read(24)
    except OSError:
        return False
    return (len(header) == 24 and header.startswith(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR")
            and int.from_bytes(header[16:20], "big") > 0
            and int.from_bytes(header[20:24], "big") > 0)


def has_capture(sauces, result, rtl):
    iteration = result.get("iterations")
    state_id = result["id"]
    if type(iteration) is not int or iteration < 1 or Path(state_id).name != state_id:
        return False
    state = sauces / "verify" / state_id
    return (has_png(state / f"iter-{iteration}" / "rendered.png")
            and (not rtl or (result.get("rtl_issues") == [] and has_png(state / "rtl.png"))))


def git(dest, *args):
    subprocess.run(["git", *args], cwd=dest, check=True, capture_output=True)


def run_fixture(name, dest, design, timeout, create_platform=None, bare=False):
    src = REPO / "examples" / "targets" / name
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns(
        ".git", ".sauces", ".dart_tool", ".gradle", ".kotlin", ".expo", "node_modules",
        "build", "dist", "Pods", "DerivedData", "xcuserdata", "local.properties",
    ))
    git(dest, "init", "-q")
    git(dest, "config", "user.name", "Sauces Eval")
    git(dest, "config", "user.email", "eval@sauces.invalid")
    git(dest, "add", "-A")
    git(dest, "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
        "commit", "-q", "-m", "fixture")
    (dest / ".sauces").mkdir(exist_ok=True)
    (dest / ".sauces" / "eval-approve").write_text("")
    if create_platform:
        (dest / ".sauces" / "eval-scaffold.json").write_text(
            json.dumps({"platform": create_platform, "bare": bare}))
    cmd = ["claude", "-p", f'/sauces:cook "{design}"', "--plugin-dir", str(REPO),
           "--permission-mode", "bypassPermissions",
           "--strict-mcp-config", "--mcp-config", json.dumps({"mcpServers": {}})]
    env = dict(os.environ)
    venv_bin = REPO / ".venv" / "bin"
    if venv_bin.is_dir():
        env["PATH"] = f"{venv_bin}{os.pathsep}{env.get('PATH', '')}"
    log = dest.parent / f"{name}.log"
    print(f"▸ {name}: running /sauces:cook (log: {log})", file=sys.stderr)
    proc = subprocess.Popen(cmd, cwd=dest, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, env=env, start_new_session=True)
    try:
        out, _ = proc.communicate(timeout=timeout)
    except BaseException:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, _ = proc.communicate()
        log.write_text((out or "") + "\n[eval] killed: timeout or interrupt\n")
        print(f"✗ {name}: cook did not finish", file=sys.stderr)
        return False
    log.write_text(out or "")
    print(f"{'✓' if proc.returncode == 0 else '✗'} {name}: cook exited {proc.returncode}",
          file=sys.stderr)
    return proc.returncode == 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run", action="store_true",
                   help="run /sauces:cook on fresh fixture copies first (costs tokens)")
    p.add_argument("--fixtures", default="flutter-bloc,empty",
                   help="comma-separated names under examples/targets/ (default: %(default)s)")
    p.add_argument("--design", default="examples/designs/login",
                   help="design input for --run (default: %(default)s)")
    p.add_argument("--results", help="folder holding one <fixture>/ result each; "
                                     "with --run it must be new or empty (default: a temp folder)")
    p.add_argument("--builds-cmd", help="verification command run in the selected project; "
                   "required for non-Flutter targets")
    p.add_argument("--create-platform", choices=SOURCE_EXTENSIONS,
                   help="scaffold this platform during --run on the empty fixture")
    p.add_argument("--bare", action="store_true",
                   help="use the bare React Native template with --create-platform react-native")
    p.add_argument("--require-captures", action="store_true",
                   help="require a PNG and a deterministic passing score for each state")
    p.add_argument("--timeout", type=int, default=3600, help="seconds per cook run (default: 3600)")
    p.add_argument("--out", help="also write the table to this markdown file")
    args = p.parse_args(argv)

    fixtures = [f.strip() for f in args.fixtures.split(",") if f.strip()]
    if not fixtures:
        print("--fixtures is empty", file=sys.stderr)
        return 2

    if args.create_platform and (not args.run or fixtures != ["empty"]):
        p.error("--create-platform requires --run --fixtures empty")
    if args.bare and args.create_platform != "react-native":
        p.error("--bare requires --create-platform react-native")

    run_status = {}
    if args.run:
        if shutil.which("claude") is None:
            print("claude CLI not found on PATH; --run needs it.", file=sys.stderr)
            return 4
        unknown = [f for f in fixtures if not (REPO / "examples" / "targets" / f).is_dir()]
        if unknown:
            print(f"unknown fixture(s): {', '.join(unknown)}", file=sys.stderr)
            return 2
        design = Path(args.design)
        design = (design if design.is_absolute() else REPO / design).resolve()
        if not design.exists():
            print(f"design not found: {design}", file=sys.stderr)
            return 2
        results = Path(args.results) if args.results else Path(tempfile.mkdtemp(prefix="sauces-eval-"))
        if results.exists() and any(results.iterdir()):
            print(f"results folder is not empty: {results}", file=sys.stderr)
            return 2
        results.mkdir(parents=True, exist_ok=True)
        print("Note: --run calls claude once per fixture. It costs tokens, needs network "
              f"and can take a long time. Results go to {results}", file=sys.stderr)
        for name in fixtures:
            run_status[name] = run_fixture(name, results / name, design, args.timeout, args.create_platform, args.bare)
    else:
        if not args.results:
            print("--results is required without --run", file=sys.stderr)
            return 2
        results = Path(args.results)
        if not results.is_dir():
            print(f"results folder not found: {results}", file=sys.stderr)
            return 2

    lines = [HEADER, RULE]
    all_passed = True
    for name in fixtures:
        cells, passed = score_fixture(results / name, name, args.builds_cmd, args.require_captures)
        if args.create_platform:
            sauces = results / name / ".sauces"
            plan = load(sauces / "plan.json") or {}
            if cells[1] != "create" or plan.get("platform") != args.create_platform:
                passed = False
        if args.run and not run_status[name]:
            passed = False
        if not passed:
            cells[-1] = "FAIL"
        all_passed &= passed
        lines.append("| " + " | ".join(cells) + " |")
    table = "\n".join(lines) + "\n"
    print(table, end="")
    if args.out:
        Path(args.out).write_text(table)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
