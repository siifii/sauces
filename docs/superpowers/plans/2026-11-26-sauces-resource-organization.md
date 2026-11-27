# Sauces Resource Organization and Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Sauces' resource layout and naming conventions clear to contributors, and keep generated target-project artifacts out of the repository.

**Architecture:** Preserve the existing Claude Code plugin roots and all resource paths consumed by the plugin. Document the resource map and ecosystem-specific naming rules, add root ignore patterns scoped to sample targets, then remove only confirmed ignored build/cache directories.

**Tech Stack:** Markdown, Git ignore rules, Git CLI, Python/pytest, Claude Code plugin validator.

**Spec:** `docs/superpowers/specs/2026-11-26-sauces-resource-organization-design.md`

## Global Constraints

- Preserve Claude Code's plugin discovery paths and the resource paths already used by skills, tests, and docs.
- Do not move the plugin's root component directories into a new umbrella directory.
- Do not mass-rename valid files or change published skill/agent/platform identifiers.
- Do not delete fixture source, platform wrappers, IDE configuration, or user changes.
- Keep each design in `examples/designs/<design-id>/` with its description and source inputs together.
- Retain the canonical `docs/superpowers/spec.md` and `plan.md`; dated specs and plans use `YYYY-MM-DD-<topic>.md` in their respective folders.
- Use Claude Code plugin kebab-case for plugin-facing Markdown resources; use language/framework conventions for code and target-project resources.
- Before touching any file, run `git status --short` and preserve all pre-existing worktree changes. Edit and commit only the paths explicitly named in each task.
- Remove only explicitly listed, confirmed generated/cache directories under `examples/targets/`; never use globs or broad recursive deletion.

---

### Task 1: Document the resource map and naming rules

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`

**Interfaces:**
- `CLAUDE.md` is the contributor policy for the canonical plugin layout, resource naming, and ecosystem-specific exceptions.
- `README.md` gives newcomers a concise resource map consistent with the contributor policy.
- No plugin-discovery path, public skill name, platform ID, or target fixture path changes.

- [ ] **Step 1: Check the worktree and current docs**

Run:

```bash
git status --short
```

Expected: identify and preserve all existing changes; do not stage or edit them.

- [ ] **Step 2: Update `CLAUDE.md`**

Add a short “Resource organization and naming” section covering:

```text
- Keep .claude-plugin/plugin.json and plugin component directories at their current paths.
- Keep each skill's SKILL.md, references/, and skill-specific assets/ together.
- Use kebab-case for plugin component names and Markdown resources; preserve required names such as SKILL.md and plugin.json.
- Keep Python module filenames snake_case, Dart file/directory names lowercase_with_underscores, and Kotlin source paths/names consistent with Kotlin conventions.
- Keep target resources in the framework's expected locations; follow an existing React Native or web project's conventions when there is no universal official layout.
- Use canonical platform IDs in references and target fixtures; variants append a descriptive suffix.
- Link to the official conventions listed in the resource-organization spec.
```

Do not duplicate the full spec or turn contributor guidance into a general platform reference.

- [ ] **Step 3: Update the README development map**

In the Development section, make the resource map explicit and accurate:

```text
.claude-plugin/  manifest and marketplace metadata
agents/          plugin agent definitions
assets/          plugin-wide assets
docs/            product docs, dated specs, and plans
examples/        designs/<design-id>/ and targets/<platform-id[-variant]>/
scripts/         plugin-side Python helpers
skills/          skill folders with SKILL.md, references/, and assets/
tests/           script, skill, and fixture tests
```

Keep the existing test/eval commands unchanged.

- [ ] **Step 4: Review the documentation diff**

Run:

```bash
git diff --check -- CLAUDE.md README.md
git diff -- CLAUDE.md README.md
```

Expected: no whitespace errors, no broken paths, and no unrelated README changes.

- [ ] **Step 5: Commit only the documentation paths**

```bash
git add -- CLAUDE.md README.md
git commit -m "docs: clarify resource organization" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>" \
  -- CLAUDE.md README.md
```

### Task 2: Ignore generated target-project output

**Files:**
- Modify: `.gitignore`

**Interfaces:**
- Root ignore patterns cover generated folders nested anywhere under `examples/targets/`.
- The rules do not ignore fixture source, `gradle/` wrappers, `.idea/`, generated platform host source, or files outside `examples/targets/`.

- [ ] **Step 1: Add target-scoped ignore patterns**

Append a clearly labelled block to `.gitignore`:

```gitignore
# Generated build and dependency output in sample target projects
/examples/targets/**/.gradle/
/examples/targets/**/.kotlin/
/examples/targets/**/build/
/examples/targets/**/.dart_tool/
/examples/targets/**/node_modules/
/examples/targets/**/.expo/
/examples/targets/**/dist/
/examples/targets/**/.next/
/examples/targets/**/ios/Flutter/ephemeral/
```

- [ ] **Step 2: Check both existing and future target paths**

Run:

```bash
git check-ignore -v --no-index \
  examples/targets/future/.gradle/probe \
  examples/targets/future/.kotlin/probe \
  examples/targets/future/build/probe \
  examples/targets/future/.dart_tool/probe \
  examples/targets/future/node_modules/probe \
  examples/targets/future/.expo/probe \
  examples/targets/future/dist/probe \
  examples/targets/future/.next/probe \
  examples/targets/future/ios/Flutter/ephemeral/probe
```

Expected: all nine paths match the new root `.gitignore` rules.

- [ ] **Step 3: Confirm source paths are not ignored**

Run:

```bash
git check-ignore -v --no-index \
  examples/targets/android-compose/src/main/AndroidManifest.xml \
  examples/targets/flutter-bloc/lib/main.dart \
  examples/targets/react-native/package.json \
  examples/targets/ios-swiftui/Fixture/FixtureApp.swift
```

Expected: no paths match an ignore rule.

- [ ] **Step 4: Check the ignore-rule diff**

Run:

```bash
git diff --check -- .gitignore
git diff -- .gitignore
```

Expected: only the target-scoped generated-output block is added.

- [ ] **Step 5: Commit only the ignore file**

```bash
git add -- .gitignore
git commit -m "chore: ignore generated target artifacts" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>" \
  -- .gitignore
```

### Task 3: Remove confirmed local generated directories

**Files:**
- Delete local ignored directories only; no tracked fixture files are changed.

**Interfaces:**
- Cleanup is restricted to the exact paths listed below.
- Do not delete anything newly appearing in the worktree unless it is re-confirmed as one of these generated directories.

- [ ] **Step 1: Verify every cleanup target**

Run:

```bash
for path in \
  examples/targets/android-compose/.gradle \
  examples/targets/android-compose/build \
  examples/targets/flutter-bloc/.dart_tool \
  examples/targets/flutter-bloc/build \
  examples/targets/flutter-bloc/ios/Flutter/ephemeral \
  examples/targets/kmp-cmp/.gradle \
  examples/targets/kmp-cmp/.kotlin \
  examples/targets/kmp-cmp/build \
  examples/targets/react-native/.expo \
  examples/targets/react-native/dist \
  examples/targets/react-native/node_modules
do
  if [ -e "$path" ]; then
    printf '%s\\n' "$path"
    git check-ignore -q "$path" || { echo "Not ignored: $path"; exit 1; }
    test -z "$(git ls-files "$path")" || { echo "Tracked content: $path"; exit 1; }
  fi
done
```

Expected: only paths that exist and are ignored are printed; no tracked content is found. If any path is not ignored or contains tracked content, stop and do not remove it.

- [ ] **Step 2: Record tracked fixture inventory**

Run and retain the output for comparison after cleanup:

```bash
git ls-files examples/targets | shasum -a 256
```

- [ ] **Step 3: Remove only the confirmed paths**

Run:

```bash
rm -rf \
  examples/targets/android-compose/.gradle \
  examples/targets/android-compose/build \
  examples/targets/flutter-bloc/.dart_tool \
  examples/targets/flutter-bloc/build \
  examples/targets/flutter-bloc/ios/Flutter/ephemeral \
  examples/targets/kmp-cmp/.gradle \
  examples/targets/kmp-cmp/.kotlin \
  examples/targets/kmp-cmp/build \
  examples/targets/react-native/.expo \
  examples/targets/react-native/dist \
  examples/targets/react-native/node_modules
```

This command may run only after Step 1 confirms the exact paths. Do not add a wildcard or any additional directory.

- [ ] **Step 4: Verify cleanup did not affect tracked fixtures**

Run:

```bash
git ls-files examples/targets | shasum -a 256
git status --short -- examples/targets
```

Expected: the hash matches Step 2 and no tracked fixture files are deleted or modified. Preserve unrelated pre-existing untracked paths.

### Task 4: Run final validation and review

**Files:**
- Verify: `.gitignore`, `CLAUDE.md`, `README.md`, and target fixture state.

- [ ] **Step 1: Confirm generated paths are ignored and removed**

Run:

```bash
for path in \
  examples/targets/android-compose/.gradle \
  examples/targets/android-compose/build \
  examples/targets/flutter-bloc/.dart_tool \
  examples/targets/flutter-bloc/build \
  examples/targets/flutter-bloc/ios/Flutter/ephemeral \
  examples/targets/kmp-cmp/.gradle \
  examples/targets/kmp-cmp/.kotlin \
  examples/targets/kmp-cmp/build \
  examples/targets/react-native/.expo \
  examples/targets/react-native/dist \
  examples/targets/react-native/node_modules
do
  test ! -e "$path" || { echo "Generated path remains: $path"; exit 1; }
done
```

Expected: command exits successfully.

- [ ] **Step 2: Run the default test suite**

Run:

```bash
.venv/bin/python -m pytest -q
```

Expected: all default tests pass.

- [ ] **Step 3: Validate plugin metadata and documentation diffs**

Run:

```bash
claude plugin validate .claude-plugin/plugin.json
git diff --check
git status --short
```

Expected: plugin validation passes; only the planned docs and ignore changes remain, plus any pre-existing user changes that were preserved.
