# Sauces Milestones 1–2 (Foundations + Flutter end to end) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A working Sauces plugin that takes the sample login design (PNG, PDF, SVG) and either follows an existing Flutter BLoC app or creates a new best-practice Flutter app, then plans, builds, verifies (golden render ≥ 90) and reports. All of it is reachable from `/sauces:cook`.

**Architecture:** The pipeline stages are markdown skills that Claude follows. Each one writes JSON into the target project's `.sauces/`, validated against a schema. Deterministic work (palette, PDF rasterizing, visual diff, lint, state/resume, report rendering, eval) lives in self-contained Python scripts. Skill behavior is tested by headless `claude -p` runs on throwaway copies of the fixtures. Script behavior is tested with pytest.

**Tech Stack:** Claude Code plugin format; Python 3.14 + Pillow + numpy (runtime), pytest (dev only); Flutter 3.41 stable (flutter_bloc, flutter_localizations/ARB, golden tests); headless Chrome to render the sample design.

**Spec:** `docs/superpowers/specs/2026-11-24-sauces-v0.1-design.md` (design, wins on conflicts) and `docs/superpowers/spec.md` (pipeline detail). Read both.

**Scope:** This plan covers design §5.10 milestones 1 and 2 only. SwiftUI, Compose, KMP/CMP and the public release each get their own plan after this one's exit check passes. They reuse every script and schema built here, adding platform rules and references.

## Global Constraints

- Skills are imperative instructions for Claude; each SKILL.md body < ~2,000 words; platform detail in `skills/<skill>/references/<platform>.md`.
- Each skill's frontmatter `description` is third person and lists its trigger phrases in quotes.
- Plugin files are referenced as `${CLAUDE_PLUGIN_ROOT}/...`; no absolute paths in shipped files.
- All working state in `.sauces/` in the target project; nothing written elsewhere except the code the user approved.
- Never overwrite an existing user component silently: extend, wrap, or ask.
- Runtime scripts run with `python3 -I`, import only stdlib + Pillow + numpy, and have `--help`. Under `-I` the script's own folder is NOT on `sys.path`, so each script is self-contained (no shared helper module). A missing Pillow or numpy prints `Missing dependency: <name>. Install with: python3 -m pip install pillow numpy` to stderr and exits 3.
- Script exit codes: 0 ok, 1 check failed (lint findings, score under threshold), 2 usage error, 3 missing dependency, 4 missing external tool.
- No hard-coded colors or user-facing strings in generated code. Localization and resources are a headline strength (design §2).
- Default fidelity threshold 90; max 3 fix iterations per screen.
- Default "keep as is" for every recommendation; only user-chosen ones are applied.
- `claude plugin validate .` passes at the end of every task that touches plugin files.
- Reference copy for the sample design (used verbatim in tests): title `Welcome back`, labels `Email` and `Password`, button `Sign in`, link `Forgot password?`, error `Incorrect email or password`. Brand color `#3D5AFE`, surface `#FFFFFF`, text `#1B1B1F`, error `#B3261E`. Canvas 390×844 logical px at device pixel ratio 2 (780×1688 PNG).

## Review Focus

1. **A Figma link with no Figma MCP connected.** Expect ingest to record the source as `unreadable` with a reason, continue with the other sources, and have cook surface the problem. Covered by a test in Task 11.
2. **Re-running cook after changing one design file.** Expect only stale stages to rerun, with no duplicate ARB keys and no duplicate components. Covered by tests in Tasks 3 and 17.
3. **A needed variant of an existing component (for example, a loading state on `AppButton`).** Expect the original file to be extended additively, never replaced. Covered by a test in Task 13.
4. **Odd images: RGBA with transparency, grayscale, or very large (4000 px).** Expect the palette and diff to handle every mode without crashing. Covered by tests in Tasks 4 and 6.
5. **Scaffold pointed at a non-empty folder.** Expect it to stop and leave the files untouched. Covered by a test in Task 16.

---

## File Structure

```
.gitignore                                  + .venv/, .sauces/verify/
requirements-dev.txt                        pillow, numpy, pytest
pytest.ini                                  markers: skill (slow, headless claude)
tests/conftest.py                           run_script(), run_skill(), fixture_copy()
tests/scripts/test_*.py                     one file per script
tests/skills/test_*.py                      one file per skill (marker: skill)
tests/data/sauces_sample/                   canned .sauces/ for report + eval tests
scripts/
  check_json.py         JSON-Schema-subset validator
  sauces_state.py       .sauces/state.json: hashing, marking, next stage
  extract_palette.py    k-means palette + ΔE merge
  rasterize_pdf.py      pdftoppm wrapper
  visual_diff.py        pixel + SSIM score, heatmap
  lint_generated.py     hard-coded color/string checks per platform
  report_render.py      audit computations + HTML fill
  eval.py               score table; --run drives headless cook
  dev/render_designs.sh dev-only: headless Chrome renders sample design
skills/
  cook/SKILL.md, references/state-schema.json, references/modes.md
  scaffold/SKILL.md, references/flutter.md, assets/flutter/**      (new skill)
  ingest/SKILL.md, references/manifest-schema.json, references/figma.md, references/images.md
  scan-project/SKILL.md, references/profile-schema.json, references/flutter.md
  plan/SKILL.md, references/plan-schema.json, references/recommendations.md
  build/SKILL.md, references/flutter.md
  verify/SKILL.md, references/flutter.md
  report/SKILL.md, assets/report-template.html
agents/ design-analyst.md, component-builder.md, fidelity-checker.md   (bodies filled)
examples/
  targets/flutter-bloc/     buildable fixture app
  targets/empty/README.md   create-mode target
  designs/login/            description.md, src/*.html, login--{default,error,loading}.png,
                            login-flow.pdf, icons/eye.svg
```

## Shared test helpers (`tests/conftest.py`, built in Task 1)

- `run_script(name: str, *args: str, env: dict | None = None) -> subprocess.CompletedProcess`: runs `sys.executable -I scripts/<name> *args` from the repo root, capturing text output.
- `fixture_copy(name: str, tmp_path: Path) -> Path`: copies `examples/targets/<name>` to `tmp_path / "my app"` (the space is deliberate) and `git init`s it with one commit, so tests can diff what Sauces changed.
- `run_skill(workdir: Path, prompt: str, timeout: int = 1800) -> subprocess.CompletedProcess`: runs `claude -p <prompt> --plugin-dir <repo> --permission-mode bypassPermissions --strict-mcp-config --mcp-config '{"mcpServers":{}}'` with `cwd=workdir`, and creates `workdir/.sauces/eval-approve` first. Use it only on `fixture_copy` directories under `tmp_path`.
- `has_tool(name) -> bool` plus `pytest.mark.skipif` for `flutter`, `pdftoppm` and `claude`.

## Schemas (key fields; later tasks rely on these names)

Every file has `"version": 1`. Paths inside `.sauces/` files are relative to the target project root.

- **manifest** (`.sauces/manifest.json`):
  - `sources[]`: `{ref, kind: figma|image|pdf|svg, status: ok|unreadable, reason?}`.
  - `screens[]`: `{id, name, states[]}`. Each state is `{id, name: default|loading|empty|error|dark|other, reference: ".sauces/references/<screen>--<state>.png", source: <index into sources>, layout?: object}`.
  - `tokens`: `colors[] {hex, name?, coverage?, origin: figma|extracted}`, `typography[] {name, size, weight, line_height?, family?}`, `spacing[] (number)`, `radii[] (number)`.
  - `assets[]`: `{path, kind: icon|illustration, name}`.
- **profile** (`.sauces/project-profile.json`):
  - `mode`: `existing|empty|ambiguous`.
  - `projects[]`:
    - `{root, platform: flutter|android-compose|ios-swiftui|kmp-cmp, architecture, state_management, di?}`
    - `theme {location, tokens_source}`
    - `localization {system: arb|string-catalog|strings-xml|compose-resources|none, rtl: bool, locales[], location?}`
    - `components[] {name, path, params[], has_preview: bool}`
    - `conventions {feature_folders: string, naming: string}`
    - `screenshot_tooling {present: bool, tool?}`
    - `findings[] {id, area: theme|colors|strings|rtl|previews|screenshot-tests|assets|accessibility, detail, paths[]}`
- **plan** (`.sauces/plan.json`):
  - Top level: `approved: bool`, `approved_by: user|eval|null`, `platform`.
  - `items[]`: `{id, design_ref, decision: reuse|extend|new|token, name, path, level: token|atom|molecule|organism|screen, existing_path?, confidence: 0..1, notes?}`.
  - `recommendations[]`: `{id, finding_id, title, why, options[] {id, label, changes[], files[]}, choice}`. The options always include `{id: "keep"}`, and `choice` defaults to `"keep"`.
  - `strings[]`: `{key, value, screen}`.
  - `dependency_changes[]`: `{package, version, scope: dev|main, reason}`.
- **state** (`.sauces/state.json`):
  - `stages`: an object with keys `ingest|scan|plan|build|verify|report`. Each value is `{status: done|pending, finished_at, inputs_hash}`.
  - `generated_files[]`, `changed_files[]`.

---

### Task 1: Repo, dev environment, test harness

**Files:**
- Create: `requirements-dev.txt`, `pytest.ini`, `tests/conftest.py`, `tests/scripts/test_help.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: the conftest helpers above; the `.venv` convention (`python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`).

- [ ] **Step 1:** `git init`, create `.venv`, install `requirements-dev.txt` (`pillow`, `numpy`, `pytest`). Add `.venv/` to `.gitignore`.
- [ ] **Step 2: Write the failing test** `tests/scripts/test_help.py::test_every_script_has_help`. It's parametrized over `scripts/*.py`: `run_script(f, "--help").returncode == 0` and the stdout contains `usage:`. Add `test_missing_dependency_message`: import `scripts/extract_palette.py` through `importlib` with `sys.modules["PIL"] = None`, call its `require_deps()`, and assert `SystemExit.code == 3`.
- [ ] **Step 3:** Run `.venv/bin/python -m pytest tests/scripts/test_help.py -v`. Expected: the missing-dependency test FAILS (no `require_deps`).
- [ ] **Step 4:** Add `require_deps() -> None` to each of the four existing stubs. It imports PIL and numpy lazily and prints the Global Constraints message on failure. Import heavy modules only after argument parsing.
- [ ] **Step 5:** Run the tests. Expected: PASS.
- [ ] **Step 6:** Commit everything in the repo (the Phase 0 scaffold plus this task): `git add -A && git commit -m "chore: scaffold plugin, dev env and test harness"`.

### Task 2: Schemas and `check_json.py`

**Files:**
- Create: `scripts/check_json.py`, `skills/ingest/references/manifest-schema.json`, `skills/scan-project/references/profile-schema.json`, `skills/plan/references/plan-schema.json`, `skills/cook/references/state-schema.json`, `tests/scripts/test_check_json.py`

**Interfaces:**
- Produces: `check_json.py <schema.json> <data.json>` exits 0 when valid and 1 with one `path: message` line per error. It supports the keywords `type`, `properties`, `required`, `items`, `enum`, `pattern`, `minimum`, `maximum`, `additionalProperties: false`. The four schemas encode the fields in "Schemas" above.

- [ ] **Step 1: Write failing tests:**
  - `test_valid_manifest_passes`: a minimal manifest with one screen and one state returns 0.
  - `test_missing_required_reports_path`: a state with no `reference` returns 1, and stdout contains `screens[0].states[0]: missing required 'reference'`.
  - `test_enum_violation`: `decision: "maybe"` returns 1.
  - `test_unknown_keyword_is_error`: a schema containing `oneOf` returns 2 with `unsupported keyword: oneOf`. Failing loudly is better than silently accepting.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement `validate(schema: dict, data: object, path: str = "") -> list[str]` and the CLI. Write the four schema files.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: json schemas and validator`.

### Task 3: `sauces_state.py` (resume and staleness)

**Files:**
- Create: `scripts/sauces_state.py`, `tests/scripts/test_sauces_state.py`

**Interfaces:**
- Consumes: the state schema (Task 2).
- Produces the CLI, where `--root` (default `.`) is the target project:
  - `hash <paths...>` prints one sha256 over the sorted (path, file bytes) pairs. Folders are walked.
  - `mark <stage> --inputs-hash H [--root .]` sets the stage to done with a timestamp and creates `state.json` if missing.
  - `next --inputs-hash H` prints the first stage that is pending, or whose `inputs_hash` differs from H for `ingest`. Every stage after a stale stage counts as stale. It prints `done` when nothing is left.
  - `add-files generated|changed <paths...>` appends without duplicates.
- Stage order is `ingest, scan, plan, build, verify, report`. Only `ingest` is keyed on the design sources hash.

- [ ] **Step 1: Write failing tests:**
  - `test_fresh_project_next_is_ingest`
  - `test_after_all_marked_next_is_done`
  - `test_changed_sources_restart_at_ingest`: mark everything done with hash A, then `next --inputs-hash B` returns `ingest`. *(Review Focus 2.)*
  - `test_add_files_dedupes`
  - `test_state_validates_against_schema`: run `check_json.py` on the written file.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: state tracking for resume`.

### Task 4: `extract_palette.py`

**Files:**
- Modify: `scripts/extract_palette.py`
- Create: `tests/scripts/test_extract_palette.py`

**Interfaces:**
- Produces: `extract_palette.py images... [-k 12] [--merge-delta-e 3.0] [-o out.json]` writes `{"version":1,"colors":[{"hex":"#RRGGBB","coverage":0.0-1.0}]}`, sorted by coverage in descending order, with coverages summing to 1 ±0.01.

- [ ] **Step 1: Write failing tests** on Pillow-generated images in `tmp_path`:
  - `test_two_color_coverage`: a 100×100 image, 70% `#FF0000` and 30% `#0000FF`, gives two colors with coverage 0.70 ±0.02 and 0.30 ±0.02.
  - `test_near_duplicates_merge`: `#3D5AFE` and `#3E5BFE` halves give one color.
  - `test_rgba_and_grayscale`: an RGBA image with alpha 0 regions (transparent pixels are ignored) and an `L`-mode image both exit 0. *(Review Focus 4.)*
  - `test_large_image_is_fast`: a 4000×4000 image finishes in under 10 s.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement:
  - Downsample to at most 200k pixels, using a seeded RNG for reproducibility.
  - Run k-means in numpy with k-means++ init, seed 0 and 20 iterations.
  - Convert to CIE Lab (D65) and merge clusters whose CIE76 ΔE is below the threshold, weighting each merged color by coverage.
  - Drop clusters under 0.5% coverage and renormalize.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: palette extraction`.

### Task 5: `rasterize_pdf.py`

**Files:**
- Modify: `scripts/rasterize_pdf.py`
- Create: `tests/scripts/test_rasterize_pdf.py`

**Interfaces:**
- Produces: `rasterize_pdf.py file.pdf --out-dir D [--dpi 144]` writes `D/page-001.png…` and prints `{"version":1,"pages":["D/page-001.png",...]}`. It exits 4 with `pdftoppm not found. Install poppler (macOS: brew install poppler; Debian/Ubuntu: apt install poppler-utils).` when the tool is missing.

- [ ] **Step 1: Write failing tests:**
  - `test_two_page_pdf` (skip if there's no pdftoppm): make a 2-page PDF with Pillow `save(..., save_all=True)` and assert two PNGs.
  - `test_missing_pdftoppm`: run with `env={"PATH": ""}` and assert exit 4 and that stderr contains `pdftoppm not found`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement with `shutil.which` + `subprocess.run(["pdftoppm","-png","-r",dpi,pdf,prefix])`, then rename the output to the zero-padded names.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: pdf rasterizing`.

### Task 6: `visual_diff.py`

**Files:**
- Modify: `scripts/visual_diff.py`
- Create: `tests/scripts/test_visual_diff.py`

**Interfaces:**
- Produces: `visual_diff.py rendered.png reference.png --out-dir D [--threshold 90]` writes `D/diff.png` (a heatmap over the dimmed reference) and `D/score.json` `{version, score, pixel_similarity, ssim, threshold, passed, size:[w,h]}`, and prints the score. It exits 0 if the score passes and 1 if not.
- Score: `score = round(100 * (0.4 * pixel_similarity + 0.6 * ssim), 1)`. `pixel_similarity` is the fraction of pixels whose max per-channel absolute difference is ≤ 16. `ssim` is the mean SSIM on luminance with a 7×7 uniform window, standard constants K1=0.01 and K2=0.03, L=255, computed from numpy cumulative sums. The rendered image is resized to the reference size with LANCZOS, and RGBA is composited on white. (Weighting is the builder's call per design §6. Recalibrate in Task 14 if an honest implementation can't reach 90, and record any change here.)

- [ ] **Step 1: Write failing tests:**
  - `test_identical_is_100`
  - `test_inverted_is_low`: the score is under 30.
  - `test_size_mismatch_resizes`: a 390×844 image against a 780×1688 one exits normally, and `size == [780,1688]`.
  - `test_rgba_transparent_vs_white_is_100` *(Review Focus 4)*
  - `test_writes_outputs_and_exit_code`: under the threshold, the exit code is 1 and `passed` is false.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: visual diff scoring`.

### Task 7: `lint_generated.py`

**Files:**
- Create: `scripts/lint_generated.py`, `tests/scripts/test_lint_generated.py`

**Interfaces:**
- Produces: `lint_generated.py --platform flutter [--allow GLOB ...] files...` prints `{"version":1,"findings":[{"file","line","rule","text"}]}`. It exits 1 if there are findings.
- Rules live in a dict, `RULES[platform] -> list[(rule_id, regex)]`, so later plans can add platforms. Flutter rules:
  - `hardcoded-color`: `Color\(0x`, `Color\.fromARGB`, `Color\.fromRGBO`, `\bColors\.(?!transparent\b)`
  - `hardcoded-string`: a non-empty string literal as the first positional argument of `Text(` or `SelectableText(`, or as the value of `hintText:`, `labelText:`, `helperText:`, `errorText:`, `tooltip:` or `semanticsLabel:`
- Lines containing `// sauces-lint-ignore` are skipped.
- (Added in Task 13) `--allow-colors GLOB` skips only the `hardcoded-color` rule for matching files (project token/theme files); string rules still apply. Files matching `--allow` globs are skipped; by default those are `**/theme/**`, `**/*_strings.dart`, `**/l10n/**` and `**/*.g.dart`.

- [ ] **Step 1: Write failing tests:**
  - `test_flags_hex_color`
  - `test_flags_text_literal`
  - `test_allows_l10n_lookup`: `Text(context.l10n.signIn)` gives no finding.
  - `test_allows_theme_folder`
  - `test_allows_strings_class`: `login_strings.dart` is skipped (design §5.2).
  - `test_ignore_comment`
  - `test_empty_string_allowed`: `Text('')` is fine.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: generated-code lint`.

### Task 8: Flutter fixture and empty target

**Files:**
- Create: `examples/targets/flutter-bloc/**`, `examples/targets/empty/README.md`, `tests/fixtures/test_flutter_fixture.py`

**Interfaces:**
- Produces a fixture with these traits, which later skill tests assert on:
  - Package `fixture_app`, feature-first layout.
  - `lib/core/theme/app_theme.dart`: M3 `ThemeData` from a seed `#3D5AFE`, plus an `AppColors extends ThemeExtension<AppColors>` with `surfaceMuted`.
  - `lib/core/widgets/app_button.dart`: `AppButton({required String label, required VoidCallback? onPressed})`.
  - `lib/core/widgets/app_text_field.dart`: `AppTextField({required String label, TextEditingController? controller, bool obscure = false, String? errorText})`.
  - `lib/core/widgets/app_card.dart`: **deliberate gap**, it uses `Color(0xFFEEEEEE)` directly.
  - `lib/features/home/` with `HomeCubit` + `HomePage`.
  - `l10n.yaml` + `lib/l10n/app_en.arb` and `app_ar.arb` (`generate: true`).
  - Inter (OFL) bundled under `assets/fonts/` and declared in pubspec with its `OFL.txt`.
  - Each widget has a widget test.
- An empty target: just a README that says it's intentionally empty.

- [ ] **Step 1: Write the failing test** `test_fixture_builds` (skip without flutter): in a copy, run `flutter pub get`, `flutter analyze --no-fatal-infos` (exit 0) and `flutter test` (exit 0).
- [ ] **Step 2:** Run. Expected: FAIL (no fixture).
- [ ] **Step 3:** Create the app with `flutter create --org dev.sauces --platforms android,ios fixture_app`, then reshape it to the traits above. Download Inter static TTFs (Regular/Medium/SemiBold) from the official Inter GitHub release.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `test: flutter fixture and empty target`.

### Task 9: Sample login design

**Files:**
- Create: `examples/designs/login/description.md`, `examples/designs/login/src/{login.css,default.html,error.html,loading.html}`, `scripts/dev/render_designs.sh`, the generated `login--default.png`, `login--error.png`, `login--loading.png`, `login-flow.pdf`, `icons/eye.svg`, `tests/fixtures/test_designs.py`

**Interfaces:**
- Produces a design with the copy, colors and canvas from Global Constraints. It uses Inter from the same TTFs as the fixture (copied into `src/fonts/`), 24 px side padding, 16 px field gaps, 12 px radii, a 52 px button height, the error state with the error text under the password field and the field border in the error color, and the loading state with a spinner replacing the button label.
- `render_designs.sh` uses `"$CHROME" --headless=new --hide-scrollbars --window-size=390,844 --force-device-scale-factor=2 --screenshot=...` per state and `--print-to-pdf` for the 3-page flow PDF. `CHROME` defaults to the macOS app path and can be overridden.

- [ ] **Step 1: Write the failing test** `test_design_files`: three PNGs exist, each is 780×1688, the PDF has 3 pages (via `rasterize_pdf.py`), and the SVG parses as XML with a `viewBox`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Author the HTML/CSS and the SVG. Run the script and commit the outputs; they're shipped as samples.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `test: sample login design`.

### Task 10: scan-project skill (Flutter + empty)

**Files:**
- Modify: `skills/scan-project/SKILL.md`
- Create: `skills/scan-project/references/flutter.md`, `tests/skills/test_scan.py`

**Interfaces:**
- Consumes: the profile schema; `check_json.py`.
- Produces: `.sauces/project-profile.json`, validated by `check_json.py` before the skill finishes. The skill fixes and re-validates on error.
- SKILL.md must:
  - detect each platform from its marker files;
  - set `mode`;
  - never modify project files;
  - collect findings only in the areas listed in the schema, each with paths;
  - load `references/<platform>.md` for heuristics.
- `flutter.md` covers:
  - state management by dependency and usage (bloc/cubit, riverpod, provider);
  - DI (get_it, injectable, riverpod);
  - theme location (`ThemeData`, `ThemeExtension`);
  - ARB/l10n detection;
  - RTL signals: `Directionality`, `EdgeInsetsDirectional`, `AlignmentDirectional`, and an `ar`/`he`/`fa`/`ur` ARB;
  - widget inventory: public `StatelessWidget`/`StatefulWidget` classes outside `features/*/` pages, with constructor params;
  - golden/screenshot tooling detection (`matchesGoldenFile`, `alchemist`, `golden_toolkit`).

- [ ] **Step 1: Write failing tests** (marker `skill`):
  - `test_scan_flutter_fixture`: `run_skill(fixture_copy("flutter-bloc"), "/sauces:scan-project")` produces a profile that validates. Assert `mode == "existing"`, platform `flutter`, `state_management == "bloc"`, `localization.system == "arb"`, `"ar" in locales`, component names ⊇ {AppButton, AppTextField, AppCard}, a `colors` finding whose paths include `lib/core/widgets/app_card.dart`, and an unchanged `git status`.
  - `test_scan_empty`: gives `mode == "empty"` and `projects == []`.
- [ ] **Step 2:** Run `.venv/bin/python -m pytest -m skill tests/skills/test_scan.py -v`. Expected: FAIL (stub skill).
- [ ] **Step 3:** Write the skill and the reference.
- [ ] **Step 4:** Run. Expected: PASS. Then run `claude plugin validate .`.
- [ ] **Step 5:** Commit `feat: scan-project for flutter`.

### Task 11: ingest skill + design-analyst agent

**Files:**
- Modify: `skills/ingest/SKILL.md`, `agents/design-analyst.md`
- Create: `skills/ingest/references/figma.md`, `skills/ingest/references/images.md`, `tests/skills/test_ingest.py`

**Interfaces:**
- Consumes: `extract_palette.py`, `rasterize_pdf.py`, `check_json.py`, the manifest schema.
- Produces: a validated `.sauces/manifest.json` and `.sauces/references/<screen>--<state>.png`. Screen and state ids are lowercase kebab-case from filenames. `<name>--<state>` is the preferred convention, followed by visual similarity, then asking the user. In eval mode, take the best guess and note it in `reason`.
- `figma.md`:
  - Use any connected tools named `get_design_context`/`get_screenshot`/`get_variable_defs`/`get_metadata`, whatever the server prefix.
  - Parse fileKey/nodeId from URLs (`node-id` with `-` → `:`, branch URLs use the branchKey).
  - Merge variables into tokens with `origin: figma`.
  - With no tools connected, write `status: unreadable` and `reason: "No Figma MCP connected. Connect the Figma connector or the plugin's figma server."`.
- `images.md`: how to call design-analyst, and how to snap observed spacing to a 4-pt grid while recording the raw values.
- design-analyst body: returns the `layout` object that's stored per state, made of `{type: column|row|stack|text|image|component, children[], text?, style?, component?: {kind, variant}, confidence}`.

- [ ] **Step 1: Write failing tests** (marker `skill`):
  - `test_ingest_login`: in a flutter-bloc copy, run `/sauces:ingest <repo>/examples/designs/login`. The manifest validates. There's one screen `login` with states {default, error, loading}. All three reference PNGs exist. The PDF source is `ok`. `assets` has `eye` as an `icon`. Token colors include one within ΔE 5 of `#3D5AFE`. The default state's layout texts include `Welcome back` and `Sign in`.
  - `test_ingest_figma_without_mcp` *(Review Focus 1)*: sources = a figma URL + the PNG folder. Exit 0, the figma source is `unreadable` with a reason mentioning `Figma`, and the PNG screens are still present.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Write the skill, references and agent.
- [ ] **Step 4:** Run. Expected: PASS. Then run validate.
- [ ] **Step 5:** Commit `feat: ingest + design-analyst`.

### Task 11b: Design-system structure signals (design §5.4a)

**Files:**
- Modify: `skills/ingest/references/manifest-schema.json`, `skills/scan-project/references/profile-schema.json`, `skills/plan/references/plan-schema.json`, `skills/ingest/SKILL.md`, `skills/ingest/references/figma.md`, `skills/scan-project/SKILL.md`, `skills/scan-project/references/flutter.md`, `tests/scripts/test_check_json.py`, `tests/skills/test_scan.py`, `tests/skills/test_ingest.py`
- Create: `skills/plan/references/design-system-patterns.md`

**Interfaces:**
- Schema additions (all optional, so existing outputs stay valid):
  - manifest `design_system`: `{signals[] {kind: figma-naming|component-set|variables|library|repetition, detail, evidence?}, component_candidates[] {name, occurrences, screens[], variants[]}}`
  - profile `projects[].component_structure`: `{pattern: atomic|layered|feature-first|custom|none, paths[], evidence[]}`
  - plan `structure`: `{recommended: atomic|layered|feature-first|follow, choice, reasons[], options[] {id, label, folders[]}}`; plan `items[].layer` (string)
- `design-system-patterns.md`: the four patterns of design §5.4a with per-platform folder mapping (Flutter now; Compose/SwiftUI/CMP rows marked "next plans"), the scoring rules from signals, and how `level` maps to `layer`.

- [ ] **Step 1: Write failing tests:** schema tests accepting the new fields and rejecting a bad `structure.recommended`; `test_scan_flutter_fixture` also asserts `component_structure.pattern == "feature-first"` (fixture: `lib/core/widgets` + `lib/features/*`); `test_ingest_login` asserts `design_system.component_candidates` names include a text field and a button with `occurrences >= 3`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement schema changes, skill/reference edits, and the patterns reference.
- [ ] **Step 4:** Run (skill tests once each). Expected: PASS. Then run validate.
- [ ] **Step 5:** Commit `feat: design-system structure signals`.

### Task 12: plan skill with recommendations

**Files:**
- Modify: `skills/plan/SKILL.md`
- Create: `skills/plan/references/recommendations.md`, `tests/skills/test_plan.py`

**Interfaces:**
- Consumes: the manifest and profile; the plan schema; the build references (Task 13 writes `skills/build/references/flutter.md`; the plan skill reads it for "what good looks like", so in this task write the plan logic against the section headings fixed in Task 13: `## Tokens`, `## Components`, `## Strings & RTL`, `## Assets`, `## Accessibility`, `## State`, `## Folders`, `## Don't`).
- Produces:
  - `.sauces/plan.md` with these sections: Summary, Components (a table), Tokens, Strings, Recommendations, Dependency changes, and a mermaid `graph LR` of screens → components → tokens.
  - A validated `.sauces/plan.json`.
- The gate:
  - Stop and ask for approval and recommendation choices in one message.
  - Write `approved: true, approved_by: "user"` only after an explicit yes.
  - If `.sauces/eval-approve` exists, approve with `approved_by: "eval"`, keep every `choice: "keep"`, and say so in the output.
- `recommendations.md`: maps each finding area to option templates, each with its concrete changes and files. Strings without localization follow design §5.2. Adding screenshot tooling is a `dependency_changes` entry that needs approval.

- Structure (design §5.4a): `plan` reads `references/design-system-patterns.md`, scores the patterns, writes `structure` with reasons, lists the pattern choice first in the approval message, and sets every item's `layer`. Eval mode takes the recommendation.

- [ ] **Step 1: Write failing tests** (marker `skill`): run scan + ingest + `/sauces:plan` in a flutter-bloc copy. Also `test_plan_structure`: `structure.recommended == "follow"` for the fixture, `choice == recommended` in eval mode, ≥ 2 `reasons`, and every item has a non-empty `layer`.
  - `test_plan_reuses_existing`: there are items whose `existing_path` ends in `app_button.dart` and `app_text_field.dart`, with a decision of `reuse` or `extend`. No `new` item is named like a button or text field.
  - `test_plan_recommendation_for_card_color`: there's a recommendation whose `finding_id` matches the colors finding, with options including `keep`, and `choice == "keep"`.
  - `test_plan_strings_cover_copy`: the `strings[].value` set contains all six copy strings from Global Constraints.
  - `test_plan_eval_approved`: `approved` is true and `approved_by` is `"eval"`.
  - `test_plan_does_not_touch_code`: `git status` is unchanged outside `.sauces/`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Write the skill and the reference.
- [ ] **Step 4:** Run. Expected: PASS. Then run validate.
- [ ] **Step 5:** Commit `feat: plan with recommendations and approval gate`.

### Task 12b: Design suggestions + `design_audit.py` (design §5.4b)

**Files:**
- Create: `scripts/design_audit.py`, `tests/scripts/test_design_audit.py`, `skills/plan/references/design-review.md`
- Modify: `skills/plan/references/plan-schema.json`, `skills/plan/SKILL.md`, `tests/skills/test_plan.py`, `tests/scripts/test_check_json.py`

**Interfaces:**
- `design_audit.py --manifest .sauces/manifest.json [-o .sauces/design-audit.json] [--grid 4]` (stdlib only) writes `{version, findings[] {id, category: accessibility|consistency|states|platform|localization|ux, severity: high|medium|low, screen, state?, detail, measured: object, guideline}}`. Importable functions (the report reuses their output, not their code): `delta_e76(hex_a, hex_b) -> float`, `near_duplicate_colors(hexes, threshold=3.0) -> list[tuple[str,str,float]]`, `contrast_ratio(fg, bg) -> float` (WCAG 2.x), `spacing_outliers(values, grid=4) -> list[float]`, `missing_states(manifest) -> dict[str, list[str]]`, `small_touch_targets(manifest, min_dp=48) -> list[dict]`, `small_text(manifest, min_px=12) -> list[dict]`. Contrast pairs come from text nodes' `style.color` over the nearest ancestor background (fallback: surface token).
- plan schema addition (optional field): `design_suggestions[] {id, audit_id?, category, severity, title, evidence, change, why, guideline, choice: keep|apply}`; `choice` defaults to `keep`.
- `design-review.md`: the category checklist of design §5.4b with per-platform conventions (Material vs HIG), how to turn audit findings into suggestions, plus judgement-based checks the script can't measure (primary-action hierarchy, error copy specificity, text-expansion risk), each requiring a cited principle.
- plan SKILL.md: run `design_audit.py`, write `design_suggestions` + a "Design suggestions" section in plan.md (sorted by severity), ask for keep/apply choices in the same approval message; eval keeps all.

- [ ] **Step 1: Write failing tests:**
  - `test_contrast_black_white_is_21` (±0.01), `test_contrast_aa_failure` (`#777777` on `#FFFFFF` < 4.5), `test_near_duplicates` (`#3D5AFE`/`#3E5BFE` flagged; `#3D5AFE`/`#B3261E` not), `test_spacing_outliers` (`[4,8,13,16]` → `[13]`), `test_missing_states` (login with only default → loading, error), `test_small_touch_target` (a 36-px-high button node flagged), `test_audit_cli_writes_findings` (canned manifest → JSON with those categories).
  - schema: plan accepts `design_suggestions` and rejects `choice: "maybe"`.
  - skill (`test_plan.py::test_plan_design_suggestions`): on the sample, ≥ 1 suggestion, every one has non-empty `guideline` and `evidence`, all `choice == "keep"` in eval mode, and plan.md has a "Design suggestions" section.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement script, schema, reference and skill changes.
- [ ] **Step 4:** Run. Expected: PASS. Then run validate.
- [ ] **Step 5:** Commit `feat: design suggestions and design audit`.

### Task 13: build skill (Flutter) + component-builder agent

**Files:**
- Modify: `skills/build/SKILL.md`, `agents/component-builder.md`
- Create: `skills/build/references/flutter.md`, `tests/skills/test_build.py`

**Interfaces:**
- Consumes: the approved plan.json, the profile, `sauces_state.py add-files`, `lint_generated.py`.
- Produces: code in the project, plus updates to `generated_files`/`changed_files` in state.json.
- SKILL.md:
  - Refuse unless `approved` is true.
  - Build in this order: tokens → assets → atoms → molecules → organisms → screens.
  - Apply only chosen recommendations, and implement every design suggestion with `choice: "apply"` as the improved design (record each in state.json `changed_files` context and in `.sauces/deviations.json` `[{suggestion_id, screen, state, region, note}]`).
  - After building, run `lint_generated.py` on the generated/changed Dart files and fix every finding.
  - Run `flutter gen-l10n` (when the project uses ARB) and `flutter analyze`, and fix errors.
  - Write a `TODO(sauces): …` for unknown behavior and list them in `.sauces/todos.json` (`[{file, line, text}]`).
- `flutter.md`, under the fixed headings (Task 12):
  - **Tokens:** `ColorScheme` + `ThemeExtension`; never `Colors.*`.
  - **Components:** `const` constructors, a `Key? key` super param, composition over inheritance; extend with an optional parameter that defaults to the old behavior.
  - **Strings & RTL:**
    - New keys go into **every** ARB file. Non-source locales get the source value plus an `@key` description `"TODO(sauces): translate"`.
    - Use ICU plurals/placeholders.
    - Use `EdgeInsetsDirectional`/`AlignmentDirectional`.
    - Directional icons use `matchTextDirection: true`.
  - **Assets:**
    - SVG icons go through `flutter_svg` if it's already a dependency. If it isn't, the plan proposes it as a `dependency_changes` entry. Until that's approved, put the SVG in `assets/icons/`, declare it in pubspec, and mark the usage `TODO(sauces): render with flutter_svg once approved`. Never add the dependency silently.
    - Raster images go in `1.0x/2.0x/3.0x` variant folders.
  - **Accessibility:** `Semantics` labels from l10n, 48 dp minimum tap targets, text scaling honored (no fixed-height text containers).
  - **State:** follow the detected pattern. For BLoC: a Cubit with an immutable state class; `TODO(sauces)` for submit logic.
  - **Folders:** follow the profile.
  - **Don't:** a short list.
- component-builder body: one plan item in, the files changed and TODOs out. It follows the reference above.

- [ ] **Step 1: Write failing tests** (marker `skill`, after scan → ingest → plan in a copy):
  - `test_build_lint_clean`: `lint_generated.py` over `generated_files + changed_files` exits 0.
  - `test_build_analyzes_and_tests`: `flutter analyze --no-fatal-infos` and `flutter test` both exit 0.
  - `test_arb_keys_in_all_locales`: `app_en.arb` and `app_ar.arb` have identical non-`@` key sets, which include ≥ 6 new keys.
  - `test_existing_components_not_replaced` *(Review Focus 3)*: for `app_button.dart` and `app_text_field.dart`, `git diff --numstat` shows deletions ≤ 3, and every pre-existing public constructor parameter is still present (regex over the old and new file).
  - `test_login_page_exists`: a file under `lib/features/login/` defines a `LoginPage` widget and a Cubit.
  - `test_files_follow_structure`: every generated file's path matches the folder of its plan item's `layer` under the chosen pattern (design §5.4a).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Write the skill, reference and agent.
- [ ] **Step 4:** Run. Expected: PASS. Then run validate.
- [ ] **Step 5:** Commit `feat: flutter build`.

### Task 14: verify skill (Flutter goldens) + fidelity-checker

**Files:**
- Modify: `skills/verify/SKILL.md`, `agents/fidelity-checker.md`
- Create: `skills/verify/references/flutter.md`, `tests/skills/test_verify.py`

**Interfaces:**
- Consumes: `visual_diff.py`, the manifest references, `generated_files`, plan `dependency_changes` (golden tooling is plain `flutter_test`, so no new dependency is needed for Flutter).
- Produces: `.sauces/verify/<screen>--<state>/iter-<n>/{rendered.png,diff.png,score.json}`, `.sauces/verify/<screen>--<state>/rtl.png`, and `.sauces/verify/summary.json` `{version, platform, threshold, renderer, results:[{id, screen, state, reference, rendered: true|false, score, passed, iterations, scores[], rtl_issues:[string], deviations:[suggestion_id], remaining:[string]}]}`, validated by `skills/verify/references/summary-schema.json`.
- `flutter.md` (verify):
  - Write `test/sauces/<screen>_render_test.dart`. *(Changed 2026-11-25: a capture-only test, not `matchesGoldenFile`. Committed goldens break on other machines' font rasterization and after every UI change; the capture test writes PNGs only with `--dart-define=SAUCES_RENDER_DIR=<dir>` and is otherwise a smoke test that fails only on exceptions/overflows. It also sets `debugShowCheckedModeBanner: false`, `debugDisableShadows = false`, and uses fixed pumps because spinners never settle.)*
  - Load the bundled fonts with `FontLoader` before pumping, since goldens otherwise use Ahem.
  - Set `tester.view.physicalSize = Size(780,1688)` and `devicePixelRatio = 2`.
  - Pump each state by giving the Cubit a seeded state.
  - Run `flutter test --dart-define="SAUCES_RENDER_DIR=$PWD/.sauces/verify/_render" test/sauces/`.
  - The RTL pass pumps with `locale: Locale('ar')`. Check for overflow errors in the test output and compare the mirrored layout, recording any issues as `rtl_issues`.
- Intentional deviations: read `.sauces/deviations.json`; list them beside the score in `summary.json` (`deviations: [suggestion_id]`) and never "fix" them back.
- Loop: when a score is below the threshold, the fidelity-checker proposes fixes, the build rules apply them, and the screen is re-rendered, for at most 3 iterations. Then record and move on. If the render fails entirely, write `rendered: false` and a manual checklist to `.sauces/verify/checklist.md`, and say so.

- [ ] **Step 1: Write failing tests** (marker `skill`, continuing the Task 13 pipeline):
  - `test_verify_scores_login`: the summary validates as JSON, the default state has `rendered: true`, `score >= 90`, and `iterations <= 3`.
  - `test_rtl_render_exists`.
  - `test_verify_does_not_change_thresholds`: every `score.json` has `threshold == 90`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Write the skill, reference and agent. **Calibration:** if an honest implementation scores under 90 only because of anti-aliasing, adjust the Task 6 tolerance or weighting (not the threshold), update its tests and record the change in the Task 6 Interfaces.
- [ ] **Step 4:** Run. Expected: PASS. Then run validate.
- [ ] **Step 5:** Commit `feat: flutter verify loop`.

### Task 15: report skill + `report_render.py`

**Files:**
- Modify: `scripts/report_render.py`, `skills/report/SKILL.md`
- Create: `skills/report/assets/report-template.html`, `tests/data/sauces_sample/**` (a canned manifest, profile, plan, state, verify summary and todos), `tests/scripts/test_report_render.py`

**Interfaces:**
- Consumes: every `.sauces/` file (missing files make their section say "not run").
- Produces:
  - `report_render.py --sauces-dir D [--template T] [-o out.html]`, which writes `report.html`.
  - The audit section renders `.sauces/design-audit.json` (Task 12b) and the plan's `design_suggestions` with their keep/apply decisions; report_render does not recompute audit facts.
- The template has sections with ids `summary`, `design-system`, `graph`, `localization`, `audit`, `todos`, `practices`, `recommendations`. `design-system` shows the chosen pattern, its reasons and components per layer. The CSS is inline. The only external resource is the mermaid CDN `<script>`, with the graph's source also shown in a `<pre>` fallback.

- [ ] **Step 1: Write failing tests:**
  - `test_audit_section_lists_suggestions`: the canned sample's design suggestions appear with their decisions and guidelines.
  - `test_render_sections`: render `tests/data/sauces_sample`, and every section id is present.
  - `test_self_contained`: no `<link rel="stylesheet"`, and the only `src=` that starts with `http` is the mermaid script.
  - `test_missing_inputs`: rendering a folder with only manifest.json exits 0 and contains `not run`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement the script and the template. Design the template so it reads like a case study: a summary card row, the graph, then the Localization & resources section (keys added/reused per locale, untranslated count, RTL issues, assets created), then the audit with color swatches. The SKILL.md runs the script and then gives the user the path and the three most important audit findings.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: report`.

### Task 16: scaffold skill (Flutter create mode)

**Files:**
- Create: `skills/scaffold/SKILL.md`, `skills/scaffold/references/flutter.md`, `skills/scaffold/assets/flutter/**` (an overlay: `lib/app.dart`, `lib/core/theme/app_theme.dart`, `lib/core/theme/app_colors.dart`, `lib/l10n/app_en.arb`, `lib/l10n/app_ar.arb`, `l10n.yaml`, `pubspec.additions.yaml`, `test/sauces/README.md`; also `lib/main.dart`, `lib/l10n/l10n.dart`, a starter `lib/features/home/view/home_page.dart`, `test/helpers/pump_app.dart` and `test/app_test.dart`, which replaces the counter `widget_test.dart` that `flutter create` writes and that fails once `main.dart` changes), `tests/skills/test_scaffold.py`

**Interfaces:**
- Consumes: profile `mode == "empty"`.
- Produces: a Flutter project at `<root>/flutter/`, plus a profile re-scan that reports `mode: existing`.
- SKILL.md:
  - Confirm the platform(s), showing defaults marked "(Recommended)" with overrides allowed. Eval mode takes the defaults. Only Flutter is implemented in this plan; other platforms say "coming in a later version" and stop.
  - Refuse a non-empty target folder unless the user confirms. In eval mode, always refuse.
  - Run `flutter create --org <org> --project-name <name> --platforms android,ios flutter`.
  - Create the folders of the design-system pattern (design §5.4a) recommended from the manifest's signals, or the one the user picks (eval mode: recommended); record it in the project README.
  - Apply the overlay and merge `pubspec.additions.yaml` (flutter_bloc, flutter_localizations, intl, `generate: true`, a fonts placeholder).
  - Run `flutter pub get`, `flutter gen-l10n` and `flutter analyze`.
  - Record the dependency versions it picked (latest stable via `flutter pub add`) and the date in the project's README.
- The multi-platform sibling layout from design §5.3 (`flutter/`, `ios/`, …, with one shared `.sauces/`) is the folder convention from now on. The other platforms plug into it in later plans.

- [ ] **Step 1: Write failing tests** (marker `skill`):
  - `test_scaffold_empty`: `/sauces:scaffold flutter` in an empty-target copy creates `flutter/pubspec.yaml`, and `flutter analyze --no-fatal-infos` and `flutter test` both exit 0 there. `lib/l10n/app_ar.arb` exists.
  - `test_scaffold_refuses_non_empty` *(Review Focus 5)*: in a folder containing `notes.txt` (eval mode), nothing is created, `notes.txt` is byte-identical, and the output mentions `not empty`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Write the skill, reference and overlay.
- [ ] **Step 4:** Run. Expected: PASS. Then run validate.
- [ ] **Step 5:** Commit `feat: flutter scaffold (create mode)`.

### Task 17: cook orchestration + `eval.py` (milestone 2 exit)

**Files:**
- Modify: `skills/cook/SKILL.md`, `README.md`
- Create: `skills/cook/references/modes.md`, `scripts/eval.py`, `tests/scripts/test_eval.py`, `tests/skills/test_cook.py`

**Interfaces:**
- Consumes: everything above.
- Produces:
  - **cook:**
    - Hash the sources and call `sauces_state.py next`.
    - Run the stages from there, printing `▸ <stage>…` and `✓ <stage> (<one-line result>)`, and marking each done.
    - Choose the mode from the profile: `existing` follows and advises, `empty` offers scaffold, `ambiguous` asks.
    - End with the report path and any unreadable sources.
  - `modes.md` holds the mode decision table from design §5.1.
  - `eval.py [--run] [--fixtures flutter-bloc,empty] [--design examples/designs/login] [--out eval.md]`:
    - Score mode reads each fixture copy's `.sauces/` and the code, and prints a markdown table with the columns `fixture | mode | builds | rendered | lint | fidelity(default) | reuse decisions | todos | PASS`. PASS means builds ∧ rendered ∧ lint ∧ fidelity ≥ 90 (design §5.11).
    - `--run` first copies each fixture to a temp folder, writes `.sauces/eval-approve`, and runs `claude -p "/sauces:cook <design>" --plugin-dir <repo> --permission-mode bypassPermissions`. It prints a notice that this costs tokens and needs network.
    - For the `empty` fixture, the build and lint columns apply to `flutter/`.

- [ ] **Step 1: Write failing tests:**
  - `test_eval_score_mode_table`: on `tests/data/sauces_sample` laid out as a fixture result, the output contains the header row and one row. Builds are checked with an injectable command, using `--builds-cmd true` in tests.
  - `test_eval_fail_row`: a sample with fidelity 80 gives a row with `FAIL`.
  - `test_cook_flutter_end_to_end` (marker `skill`): `/sauces:cook <design>` on a flutter-bloc copy produces `report.html`, every stage in `state.json` marked `done`, and a summary score ≥ 90.
  - `test_cook_rerun_is_idempotent` *(Review Focus 2)*:
    - Run cook a second time with no changes. The output says nothing is left to do, and `git status` is identical to the first run's.
    - Then touch `login--error.png` with a 1-px change and run again. Ingest reruns, the ARB files have no duplicate keys, and `generated_files` has no duplicates.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Write the skill and `eval.py`. Update the README's usage, modes, requirements (`pip install pillow numpy`, poppler, Flutter) and a "Localization & resources" highlight.
- [ ] **Step 4:** Run all tests: `.venv/bin/python -m pytest -v` and `.venv/bin/python -m pytest -m skill -v`. Expected: PASS.
- [ ] **Step 5:** **Milestone 2 exit:** `.venv/bin/python scripts/eval.py --run --fixtures flutter-bloc,empty` passes both rows. Commit `eval.md` as the baseline, and `claude plugin validate .` passes.
- [ ] **Step 6:** Commit `feat: cook orchestration and eval; milestone 2`.

### Task 18: Hardening and test matrix (added 2026-11-24 at the user's request: "test it well")

**Goal:** Prove Sauces holds up beyond the one fixture and one design it was built against, and that LLM-driven stages are stable across runs.

**Files:**
- Create: `examples/targets/flutter-riverpod/` (Riverpod + go_router, `lib/src/` layout, **no** localization, a `functions/` Firebase folder beside the app, one hard-coded string), `examples/targets/flutter-atomic/` (BLoC, `lib/design_system/{atoms,molecules,organisms}`, ARB en only, no RTL), `examples/designs/onboarding/` (3 screens: welcome, list with items, empty list; plus a dark-mode variant of welcome; rendered like Task 9), `tests/skills/test_matrix.py`, `scripts/dev/stability.sh`, `docs/superpowers/test-report-m2.md`
- Modify: `scripts/eval.py` (fixture × design matrix)

- [ ] **Step 1: Fixture tests first:** each new fixture builds (`flutter analyze`, `flutter test`) and has exactly its documented lint gaps (pure-Python test, like Task 8).
- [ ] **Step 2: Matrix skill tests** (`test_matrix.py`, marker `skill`):
  - riverpod fixture: scan gives `state_management == "riverpod"`, `localization.system == "none"`, mode `existing` (NOT `ambiguous` despite `functions/`), a `strings` finding; plan recommends `follow`; build puts strings in a feature strings class (design §5.2) and lint passes; a recommendation offers proper localization.
  - atomic fixture: scan gives `component_structure.pattern == "atomic"`; plan recommends `follow` and new components land in the atomic layers.
  - onboarding design into the **empty** target: ingest finds 3 screens and a `dark` state; create mode recommends a pattern from the scoring table with reasons; design suggestions include a missing-state finding; scaffold + build + verify pass the eval gates.
- [ ] **Step 3: Stability:** `scripts/dev/stability.sh` runs every skill test 3× and reports pass rate per test. Target 100%; anything flaky gets its root cause fixed (tighter instructions or a less brittle assertion), never a retry loop.
- [ ] **Step 4: Real-world smoke (read-only):** shallow-clone 3 public open-source Flutter apps of different styles into the scratch folder (never committed), run `scan-project` and `plan` (eval mode) on each, and record in `test-report-m2.md`: valid JSON (yes/no), detected stack vs actual, findings quality, any crash or misleading output. Every real defect found becomes a fix with a regression test.
- [ ] **Step 5: Visual check:** for every rendered screen in the matrix, the controller views rendered.png beside the reference and diff.png and records a one-line judgement in the test report (a score ≥ 90 that still looks wrong is a defect).
- [ ] **Step 6:** `scripts/eval.py --run` over the full matrix; commit `eval.md` and `test-report-m2.md`; commit `test: hardening matrix, stability and real-world smoke`.
