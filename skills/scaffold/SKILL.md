---
name: scaffold
description: >-
  This skill should be used when the user asks to "create a new app", "scaffold a project", "start a new Flutter app", "set up a project from scratch", "I don't have a project yet", or runs "/sauces:scaffold". Creates a new project in an empty folder (create mode) with the official tooling, then adds Sauces' structure: the chosen design-system folders, a platform theme, localized resources, seedable state and test support.
argument-hint: "[flutter|ios|android|kmp|react-native|react|html ...] [--org <reverse.domain>] [--name <project_name>] [--bare] [--next]"
---

# Scaffold

Create a new, buildable project for the design in an empty folder, so the rest of the pipeline (plan, build, verify) can follow it like any existing project.

## Hard rules

- The target root is the current working directory. Each platform gets a sibling folder under it (`flutter/`, `ios/`, `android/`, `kmp/`, `react-native-app/`, `web-app/`, `web-html/`), with one shared `.sauces/` at the root.
- Never create, change or delete anything outside the new platform folder and `.sauces/`. Never modify a file that existed before scaffold ran, except Sauces' own `.sauces/` state (the files the steps below name).
- Use the platform reference and official creation tooling. Use a bundled overlay where the reference provides one. Preserve template dependency versions and resolve additions through the platform tool.
- Eval mode (`.sauces/eval-approve` exists): never ask. Take every default marked (Recommended) and refuse a non-empty folder (step 2 gives the exact wording).

## 1. Platforms

Parse `$ARGUMENTS`: platform words (`flutter`, `ios`, `android`, `kmp`, `react-native`, `react` or `web`, `html`), `--org <org>`, `--name <name>`, `--bare` (React Native only, to use the Community CLI) and `--next` (web-react only, Next.js instead of Vite).

- No platform given: ask which to create, offering `Flutter (Recommended)`, `iOS (SwiftUI)`, `Android (Compose)`, `Kotlin/Compose Multiplatform`, `React Native (Expo)`, `Web: React (Vite)` and `Web: HTML/CSS (no build)`, several allowed. In eval mode with no explicit platform, use the platform ID in .sauces/eval-scaffold.json when present (translate it to the corresponding scaffold argument); otherwise use Flutter. Honor `bare: true` from that file only with React Native. Explicit platform and template flags still apply.
- Map argument → platform reference ID → destination: `flutter → flutter → flutter/`, `ios → ios-swiftui → ios/`, `android → android-compose → android/`, `kmp → kmp-cmp → kmp/`, `react-native → react-native → react-native-app/`, `react → web-react → web-app/` (`web` is a synonym), `html → web-html → web-html/`. Deduplicate selections and reject unknown arguments before writing. Reject --bare unless React Native is selected, and --next unless web-react is selected. Follow the web references in order, like React Native in step 4; they skip the org question (web has no bundle ID).

## 2. Check the folder is empty

First read `.sauces/project-profile.json` if it exists. If its `mode` is not `empty` (`existing` or `ambiguous`), stop and say what the scan found, in eval mode too, and make no changes. Then run the folder check below as a second, stricter guard.

The root counts as empty when every entry in it is one of:

- a dotfile or dot-folder (`.git/`, `.sauces/`, `.gitignore`, `.DS_Store`, `.editorconfig`, `.github/`, `.vscode/`, `.idea/`);
- `README*`, `LICENSE*`, `LICENCE*`, `CHANGELOG*`, or a `docs/` folder;
- a design input: an image, PDF or SVG file, or a folder holding only such files plus their notes (`.md`/`.txt` files inside that folder, such as `description.md`).

Anything else (for example `notes.txt`, `src/`, a `package.json`) makes it **not empty**. If any selected destination already exists (including a symlink), stop and name it. Make no changes. If the user has just completed a requested wizard handoff, resume step 4 with that exact template and do not run the wizard again.

When the folder is not empty:

- Eval mode: your reply is this exact sentence, word for word: "This folder is not empty (<up to 5 entries>), so Sauces won't scaffold here. Run it in an empty folder." Make no changes and stop.
- Otherwise, list up to 10 of the unexpected entries, say they will be left untouched and the projects go into the selected platform folders, and ask whether to continue. Stop unless the user says yes.

## 3. Choices

Load `${CLAUDE_PLUGIN_ROOT}/skills/scaffold/references/<platform-id>.md` for each selected platform. Each is binding. Work out the defaults, then confirm them in one question (skip the question in eval mode):

1. **Project name**: `--name`, else the default from the reference (section 1). For Flutter use the Flutter reference defaults and validation. For native targets, derive the default from the design or use SaucesApp, and validate the platform identifier and bundle/package ID before creation. For mixed targets derive a compliant identifier per template (for example `sauces_app` for Flutter and `SaucesApp` for Xcode).
2. **Org**: `--org`, else `com.example`.
3. **Design-system structure**: score `atomic`, `layered` and `feature-first` with `${CLAUDE_PLUGIN_ROOT}/skills/plan/references/design-system-patterns.md` section 4 from `.sauces/manifest.json` (`follow` is never offered in create mode). Without a manifest, recommend `feature-first`. Show the recommended one with its reasons, as in that file's section 5, and the others as alternatives.
4. **Locales**: `en` (template) and `ar` (Recommended: it proves right-to-left layouts from day one). The user may add or remove locales; `en` always stays.

## 4. Create

For Android, iOS, KMP and React Native, follow the chosen reference in order. Track completed platforms during a template handoff. For Flutter, follow its reference in this order:

1. Create the project (section 2), add the dependencies and edit `pubspec.yaml` (section 3).
2. Apply the overlay with the placeholders filled (section 4) and the seed color (section 5). For each extra locale, add `lib/l10n/app_<locale>.arb` with the same keys as `app_en.arb`, the English text, and an entry in `.sauces/todos.json` (`{"file": "flutter/lib/l10n/app_<locale>.arb", "line": 1, "text": "translate N new strings"}`; create the file as `[]` if it is missing). If `ar` was removed, delete `app_ar.arb`, and delete the right-to-left test in `test/app_test.dart` unless another right-to-left locale (`he`, `fa`, `ur`) is chosen, in which case point it at that locale.
3. Create the structure folders (section 6).
4. Run the checks (section 7) and fix the files you wrote until every check passes. After 3 failed rounds, stop and report the failing output verbatim. Do not hide errors.
5. Append the README section (section 8).

## 5. Record and rescan

1. Record the completed platform directories as generated (Flutter example):

   ```bash
   python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/sauces_state.py" add-files generated flutter
   ```

2. Run the scan-project skill (`/sauces:scan-project`) so `.sauces/project-profile.json` describes each completed platform with its exact destination as root. A single supported app has mode `existing`. Several side-by-side apps have mode `ambiguous`; use scan’s project choice before continuing with cook.

## 6. Report

If you stopped in step 2, your whole reply is the refusal sentence from step 2 followed by at most one line listing the entries. Nothing else.

Otherwise:

Reply in at most ~120 words:

- What was created and where, the project name, org and toolchain versions.
- The structure chosen and the main folders, the locales, and the dependency versions picked.
- Build, lint, and test results per target, including any unavailable tools or devices.
- Next step: `/sauces:plan` (or `/sauces:cook` to run the rest of the pipeline). If the org is `com.example`, remind the user to change it before publishing.
