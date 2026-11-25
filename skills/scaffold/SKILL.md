---
name: scaffold
description: This skill should be used when the user asks to "create a new app", "scaffold a project", "start a new Flutter app", "set up a project from scratch", "I don't have a project yet", or runs "/sauces:scaffold". Creates a new project in an empty folder (create mode) with the official tooling, then adds Sauces' structure: the chosen design-system folders, a Material 3 theme with token extensions, ARB localization with a right-to-left locale, state management and test helpers.
argument-hint: [flutter|ios|android|kmp ...] [--org <reverse.domain>] [--name <project_name>]
---

# Scaffold

Create a new, buildable project for the design in an empty folder, so the rest of the pipeline (plan, build, verify) can follow it like any existing project.

## Hard rules

- The target root is the current working directory. Each platform gets a sibling folder under it (`flutter/`, later `ios/`, `android/`, `kmp/`), with one shared `.sauces/` at the root.
- Never create, change or delete anything outside the new platform folder and `.sauces/`. Never touch a file that existed before you started.
- Use the platform's official creation tool, then the overlay in `${CLAUDE_PLUGIN_ROOT}/skills/scaffold/assets/<platform>/`. Dependency versions come from the package manager (latest stable that resolves), never typed by hand.
- Only Flutter is implemented in this version.
- Eval mode (`.sauces/eval-approve` exists): never ask. Take every default marked (Recommended), refuse a non-empty folder, and say what you decided in the summary.

## 1. Platforms

Parse `$ARGUMENTS`: platform words (`flutter`, `ios`, `android`, `kmp`), `--org <org>` and `--name <name>`.

- No platform given: ask which to create, offering `Flutter (Recommended)`, `iOS (SwiftUI)`, `Android (Compose)` and `Kotlin/Compose Multiplatform`, several allowed. Eval mode: Flutter.
- For each platform other than Flutter, say: "<Platform> scaffolding is coming in a later version of Sauces." If Flutter is not among the chosen platforms, stop there.

## 2. Check the folder is empty

The root counts as empty when every entry in it is one of:

- a dotfile or dot-folder (`.git/`, `.sauces/`, `.gitignore`, `.DS_Store`, `.editorconfig`, `.github/`, `.vscode/`, `.idea/`);
- `README*`, `LICENSE*`, `LICENCE*`, `CHANGELOG*`, or a `docs/` folder;
- a design input: an image, PDF or SVG file, or a folder holding only such files plus their notes (`.md`/`.txt` files inside that folder, such as `description.md`).

Anything else (for example `notes.txt`, `src/`, a `package.json`) makes it **not empty**. If a `flutter/` entry exists, stop: "There is already a flutter/ folder here. Sauces won't overwrite it." Make no changes.

When the folder is not empty:

- Eval mode: begin your reply with this exact sentence, word for word (tooling matches it): "This folder is not empty (<up to 5 entries>), so Sauces won't scaffold here. Run it in an empty folder." Make no changes and stop.
- Otherwise, list up to 10 of the unexpected entries, say they will be left untouched and the project goes into `flutter/`, and ask whether to continue. Stop unless the user says yes.

## 3. Choices

Load `${CLAUDE_PLUGIN_ROOT}/skills/scaffold/references/flutter.md`. It is binding. Work out the defaults, then confirm them in one question (skip the question in eval mode):

1. **Project name**: `--name`, else the default from the reference (section 1). Validate it; on an invalid `--name`, say why and stop.
2. **Org**: `--org`, else `com.example`.
3. **Design-system structure**: score `atomic`, `layered` and `feature-first` with `${CLAUDE_PLUGIN_ROOT}/skills/plan/references/design-system-patterns.md` section 4 from `.sauces/manifest.json` (`follow` is never offered in create mode). Without a manifest, recommend `feature-first`. Show the recommended one with its reasons, as in that file's section 5, and the others as alternatives.
4. **Locales**: `en` (template) and `ar` (Recommended: it proves right-to-left layouts from day one). The user may add or remove locales; `en` always stays.

## 4. Create

Follow the reference, in order:

1. Create the project (section 2), add the dependencies and edit `pubspec.yaml` (section 3).
2. Apply the overlay with the placeholders filled (section 4) and the seed color (section 5). For each extra locale, add `lib/l10n/app_<locale>.arb` with the same keys as `app_en.arb`, the English text, and an entry in `.sauces/todos.json` (`{"file": "flutter/lib/l10n/app_<locale>.arb", "line": 1, "text": "translate N new strings"}`; create the file as `[]` if it is missing). If `ar` was removed, delete `app_ar.arb`, and delete the right-to-left test in `test/app_test.dart` unless another right-to-left locale (`he`, `fa`, `ur`) is chosen, in which case point it at that locale.
3. Create the structure folders (section 6).
4. Run the checks (section 7) and fix the files you wrote until every check passes. After 3 failed rounds, stop and report the failing output verbatim. Do not hide errors.
5. Append the README section (section 8).

## 5. Record and rescan

1. Record the project:

   ```bash
   python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/sauces_state.py" add-files generated flutter
   ```

2. Run the scan-project skill (`/sauces:scan-project`) so `.sauces/project-profile.json` describes the new project (`mode: "existing"`, a `flutter` project with `root: "flutter"`). If the profile does not say that, report it as a problem.

## 6. Report

Reply in at most ~120 words:

- What was created and where (`flutter/`), the project name, org and Flutter version.
- The structure chosen and the main folders, the locales, and the dependency versions picked.
- That `flutter analyze` and `flutter test` pass.
- Next step: `/sauces:plan` (or `/sauces:cook` to run the rest of the pipeline). If the org is `com.example`, remind the user to change it before publishing.
