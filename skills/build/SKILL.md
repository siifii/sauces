---
name: build
description: This skill should be used when the user asks to "build the approved plan", "implement the components", "generate the UI code", "write the screens", "implement the design in my app", or runs "/sauces:build". Implements an approved .sauces/plan.json in the project's own architecture and conventions (tokens, assets, atoms, molecules, organisms, screens), localized and accessible, applies only the chosen recommendations and design suggestions, then lints, analyzes and tests the result.
---

# Build

Turn the approved `.sauces/plan.json` into code the project's developers would merge without rewriting: their structure, names, state management, theme and localization.

## Hard rules

- The target root is the current working directory. Plan and state paths are relative to it.
- Refuse to start unless `.sauces/plan.json` has `"approved": true`. Say: "The plan isn't approved yet. Run `/sauces:plan` and approve it first." and stop.
- Build only what the plan lists. Apply only recommendations whose `choice` is not `keep` and design suggestions whose `choice` is `apply`. Everything else follows the project as it is.
- Never overwrite, rename, move or delete an existing user file or component. `extend` means additive optional parameters whose defaults reproduce today's behavior exactly; existing call sites and tests keep passing.
- Never change an existing theme value or role unless a chosen `theme` recommendation says so. New tokens are additive.
- No hard-coded colors or user-facing strings in generated or changed code, tests included. Every new string goes into every locale.
- Never add a package that is not in `dependency_changes`.
- Behavior the design does not show (API calls, navigation, validation rules) is a `// TODO(sauces): …` comment, never a guess or a fake (no delays, no stub success).
- Working files go in `.sauces/` only.

## 1. Load

1. Read `.sauces/plan.json`. Check `approved` (above). If it is missing, tell the user to run `/sauces:plan` (or `/sauces:cook`).
2. Read `.sauces/project-profile.json` and match the project by `plan.platform` and `plan.project_root`. For a legacy plan without `project_root`, proceed only if there is exactly one match by platform; otherwise ask for a fresh plan. Run tools in that project root. Treat plan file paths as relative to the target root and do not prepend the project root again. Read `.sauces/manifest.json` for the design values and the reference images in `.sauces/references/`; look at the reference image of every state before building its screen.
3. Read the build reference for the platform: `${CLAUDE_PLUGIN_ROOT}/skills/build/references/<platform>.md`. It is binding: every section (`## Tokens` … `## Don't`) applies to every file you write. If no reference exists for the platform, stop and say that building for it arrives in a later Sauces version.
4. Read the source of every component the plan reuses or extends, the theme files (`theme.location`, `theme.tokens_source`), the localization config and source-locale string file, the nearest existing feature (page, state, tests) and the project's test helpers. Match their style: imports, naming, file layout, formatting.
5. Run `git status --porcelain` in the project root when it is a git repository and remember which files were already modified, so the summary separates your changes from the user's.

## 2. Gather the decisions

From `plan.json` collect:

- `structure.choice`: where new files go (each item's `path` and `layer` already follow it).
- Chosen recommendations: every `recommendations[]` entry with `choice` ≠ `keep`, with the option's `changes` and `files`. Apply each exactly as listed, in the build-order step it belongs to (theme and token changes first). `finding_id`s such as `design-theme-*` or `strings-localization` have no scan finding behind them; that is expected.
- Applied design suggestions: every `design_suggestions[]` entry with `choice: "apply"`. Its `change` replaces what the design shows for the affected element (section 4).
- `dependency_changes`: add each package with the platform's tool (see the platform reference; Flutter: `flutter pub add <package>:<version>`, `dev:<package>` for `scope: "dev"`) before writing code that uses it.

## 3. Build in order

Build items in this order: tokens → assets → atoms → molecules → organisms → screens. Within a level, follow item ids. For each item:

| `decision` | What to do |
|---|---|
| `token` | Add the token additively where the item's `path` says (a new theme-extension field, a new text style). Never change existing tokens. |
| `reuse` | Nothing to write for the component. The screen calls it with the parameters the item's `notes` list. |
| `extend` | Add exactly the parameter or variant the `notes` name, with the stated default. Minimal diff: touch only the lines the new parameter needs, don't reformat the file. Append a test for the new behavior to the component's existing test file. |
| `new` | Create the file at `path`, following the reference's Components section, with a preview or test per its Previews and tests section. |
| `screen` level | Create the screen at `path` and its state next to it (reference: State, Folders). Wire every design state to the state class so each state can be shown by seeding it (default, error, loading…). Add a screen test that pumps each state and one right-to-left locale when the project has one. |

Record each generated path with `sauces_state.py add-files generated` immediately after creating it. Record edited paths with `add-files changed` as soon as each edit is saved. Leave the build stage pending until the checks pass. This lets a retry recognize files from an interrupted build.

Before creating a file at a `new` path, check that it does not exist. If it exists and is listed in `.sauces/state.json` `generated_files`, it is from an earlier build: update it in place. If it exists and is not listed, it is the user's: do not touch it; ask the user how to proceed (in eval mode skip the item and report it).

Read each item's `notes` first: kept-theme fidelity differences (leave them; verify reports them), icon substitutions, the `TODO(sauces)` behavior to leave.

**Inline or delegated.** Build inline by default: one agent seeing the whole plan keeps names and imports consistent, and each dispatch costs a fresh context. Delegate an item to the `component-builder` agent only when the plan has more than about eight `new`/`extend` items or the user asks for it. Then dispatch one agent per item, sequentially in build order (later items import earlier ones), passing the item, the relevant profile fields, the platform reference path and the files earlier items created. Each agent returns the files it created or changed, the string keys it used and its TODOs; collect them for steps 4, 6 and 7. Agents never edit string resources: this skill owns every ARB/strings edit (step 4.1), so add the keys an agent reports before running the checks.

## 4. Strings, resources and applied suggestions

1. You own every string edit (component-builder agents only report keys). Add every `strings[]` entry, plus keys for accessibility labels and tooltips (show/hide password), with the project's own mechanism, per the reference's Strings section (ARB: every locale; non-source locales get the source value and a `TODO(sauces): translate` description). Keep existing entries and formatting. Text that varies uses placeholders and plurals.
2. Regenerate localizations and fix every error (Flutter: `flutter gen-l10n` when `l10n.yaml` exists or `generate: true` is set).
3. Add assets per the reference's Assets section (declared in the manifest file, resolution variants, no unapproved packages).
4. For each applied design suggestion, build the `change` as written (for example extend a hit area, raise a text size, add a missing state). Add any string or token it needs the same way as above. Then append to `.sauces/deviations.json` one entry per affected screen state:

   ```json
   {"suggestion_id": "sug-1", "screen": "login", "state": "default", "region": "column > link \"Forgot password?\"", "note": "Hit area extended to 48 dp (lib/features/login/view/login_page.dart); text position unchanged"}
   ```

   `screen`/`state`/`region` come from the suggestion's `evidence`; `note` says what was built and the files. A hit-area-only change still gets an entry. Write `[]` when no suggestion was applied. Record the files the suggestion touched with the other files in step 7.

## 5. Check and fix

For a platform other than Flutter, run the platform reference's Checks. Run step 5.1 on the changed UI source files (Kotlin, Swift, or JavaScript/TypeScript) with the selected platform ID, including the same token-file allowances, scope and JSON output. Apply the extend self-check in step 5.5 and report unavailable tooling and any checks it prevented.

For Flutter, run the following from the project root and fix every problem, then run the checks again until they pass. Never silence a check (no `// ignore:` comments, no `sauces-lint-ignore`, no removed tests) unless the finding is a false positive you can explain in the summary.

1. Lint every Dart file you created or changed, tests included:

   ```bash
   python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/lint_generated.py" --platform flutter \
     --allow-colors "<theme.tokens_source>" --allow-colors "<chosen pattern's tokens folder>/**" <files...>
   ```

   Run it from the project root with relative paths. The files are everything you created or changed: your list, plus any path `git status --porcelain` shows now that was not in the step 1.5 list. `--allow-colors` lets color literals stand in the project's token files (the profile's token source, dedicated token files listed in the approved plan, or the chosen pattern's tokens folder) while string rules still apply there; leave out one that does not apply. The `theme/`, `l10n/` and `*_strings.dart` defaults are built in. Exit 0 is clean. Exit 1 prints JSON findings (`file`, `line`, `rule`, `text`): move each color to a token and each string to the localization system. In an existing file you changed, fix only findings on lines you wrote; a finding on a line that was already there (`git diff -U0`; files dirty before step 1.5 are the user's work in progress) is the user's code: leave it and list it in the summary. Without git, lint new files whole and, in changed files, only the lines of the symbols the plan told you to add. Exit 2 is a usage error (a missing file): fix the paths.

   Once lint passes (or only the user's own lines are left), run it one last time with the same arguments and save its JSON output to `.sauces/lint.json` at the target root (append `> "<target root>/.sauces/lint.json"`; from the target root itself that is `> .sauces/lint.json`). The report reads it; a non-zero exit there is expected when user lines remain.
2. `flutter gen-l10n` again if you touched ARB files since step 4.
3. `dart format` the files you created (not the existing files you extended; see the reference's Extend rules).
4. `flutter analyze --no-fatal-infos`: fix every error and warning in files you touched. Report pre-existing issues in other files without fixing them.
5. Extend self-check: `git diff` each file you extended. Only added lines plus the few lines the new parameter must touch (the constructor, the expression that uses it) may differ; anything else (reformatting, reordering, a changed default) means: restore the file (`git checkout -- <file>` when it was clean before step 1.5) and redo the extension.
6. `flutter test`: every test passes, the project's existing tests included. A failing existing test means your change broke behavior: fix your code, not the test.

If a tool is missing (`flutter` not on `PATH`), skip the steps that need it, say so plainly in the summary, and never claim the code was analyzed or tested.

## 6. TODOs

Search the files you created or changed for `TODO(sauces)` and write `.sauces/todos.json`, a JSON array sorted by file then line:

```json
[{"file": "lib/features/login/cubit/login_cubit.dart", "line": 21, "text": "call your auth repository with state.email and state.password, then emit LoginStatus.success or LoginStatus.failure."}]
```

`file` is relative to the target root, `line` is 1-based and points at the line containing `TODO(sauces)`, `text` is the text after `TODO(sauces): `. List the `TODO(sauces): translate` descriptions of a non-source ARB file as one entry per file: `line` of its first occurrence, `text` `"translate N new strings"`. Write `[]` when there are none.

## 7. Record state

Record every file under the project root, relative paths, in one call each (`generated` = files you created, `changed` = existing files you edited: components, ARB files, `pubspec.yaml`, theme files). Leave out the generated l10n output and anything under `.sauces/`.

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/sauces_state.py" add-files generated <created files...>
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/sauces_state.py" add-files changed <edited files...>
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/sauces_state.py" mark build
```

Mark build only after section 5 passes (or the tool-missing case is reported).

## 8. Summary

End with a short message:

- Files created and changed, grouped by level, with each `extend` and the parameter it added.
- Strings added (count, keys) and locales that need translation.
- Recommendations applied and design suggestions applied (with their deviations), or "none: everything kept as is".
- Checks: lint, gen-l10n, analyze and test results (or which were skipped and why).
- Expected differences from the design the plan accepted (kept theme roles, icon substitutions).
- The TODO count with the first few, and the next step: `/sauces:verify`.
