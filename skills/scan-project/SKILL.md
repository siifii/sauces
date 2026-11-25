---
name: scan-project
description: This skill should be used when the user asks to "scan the project", "detect the architecture", "inventory components", "find the theme and design tokens", "what UI toolkit does this app use", or runs "/sauces:scan-project". Profiles an Android Compose, iOS SwiftUI, KMP/CMP, React Native or Flutter project into .sauces/project-profile.json.
---

# Scan project

Profile the target project and write `.sauces/project-profile.json`. The profile drives the mode (`follow` / `advise` / `create`) and the advise findings that `plan` turns into recommendations, so record only what the code shows. Never guess.

## Hard rules

- The target root is the current working directory. Every path in the profile is relative to it, POSIX style (`lib/core/widgets/app_card.dart`, never absolute, never `./lib/...`).
- Read only. Never create, edit, format, delete or move any project file. Never run `flutter pub get`, `gradle`, `xcodebuild`, code generators or anything else that writes into the project. The single file you write is `.sauces/project-profile.json` (create `.sauces/` if missing; leave everything else in `.sauces/` untouched).
- Never invent a value. Use `"unknown"` for a required string you cannot determine with confidence, `[]` for an empty list, and leave optional fields out.
- Skip these folders everywhere: `build/`, `.dart_tool/`, `Pods/`, `node_modules/`, `.git/`, `.sauces/`, `.gradle/`, `.idea/`, `DerivedData/`, and generated code folders (for example a gitignored `lib/l10n/gen/`).

## 1. Find projects

Look for marker files at the target root and in each direct child folder (one level down), so sibling layouts (`flutter/`, `ios/`, `android/`, `kmp/`) and simple monorepos are found.

| Platform id | Marker files |
|---|---|
| `flutter` | `pubspec.yaml` that depends on `flutter: sdk: flutter` |
| `ios-swiftui` | `*.xcodeproj` or `Package.swift` with Swift sources that `import SwiftUI` and an iOS target or declared iOS support |
| `android-compose` | `build.gradle(.kts)` / `settings.gradle(.kts)` with Compose enabled in the root or an included app module (`buildFeatures { compose = true }`, the `org.jetbrains.kotlin.plugin.compose` plugin, or `androidx.compose` dependencies) |
| `kmp-cmp` | Gradle build with `kotlin("multiplatform")` / `org.jetbrains.kotlin.multiplatform` in the root or an included module, with `org.jetbrains.compose`, shared composables in `src/commonMain`, and at least one mobile target |
| `react-native` | App package with a runtime `react-native` dependency or an Expo app dependency and a mobile entry point or routes |

Then reconcile:

- Resolve candidate roots from their build descriptors and host relationships before classifying. A Flutter project's own host folders (`android/`, `ios/`, `macos/`, `web/`, `linux/`, `windows/` inside the Flutter root, recognisable by `GeneratedPluginRegistrant`, `Flutter/` xcconfigs, or the `dev.flutter.flutter-gradle-plugin` plugin in `settings.gradle(.kts)`; `flutter.sdk` lives in the usually gitignored `local.properties`, so do not rely on it) are part of that Flutter project. Never report them as separate projects.
- Treat React Native Android and iOS host folders and Expo-generated projects as part of their JS app when build files load React Native or use Expo autolinking. For a JS workspace, inspect packages declared in local workspace metadata for app entry points. Ignore React Native libraries without a runnable app.
- Likewise, a KMP project's `androidApp/` / `iosApp/` folders belong to the KMP project. Record native UI in them under that one `kmp-cmp` entry.
- An Android Gradle project without Compose (XML Views only) or an iOS project with only UIKit is not a supported target. Treat it as an unsupported app project.
- Backend, cloud-function, tooling and script folders (for example Firebase `functions/`, `backend/`, `server/`, `api/`, `scripts/`, `tools/`, infrastructure code) are not app/UI projects. Ignore them for mode selection and mention them in the summary.

Set `root` to the project folder relative to the target root: `"."` for the root itself, `"flutter"` for a child folder.

## 2. Set the mode

- `existing`: a supported project was found and none of the ambiguous conditions below apply. List them all in `projects`, ordered by platform: `flutter`, `ios-swiftui`, `android-compose`, `kmp-cmp`, `react-native`.
- `empty`: no supported project and no source code at all. A folder with only README/docs, licences, dotfiles or images is empty. Write `projects: []`.
- `ambiguous`: one of these holds:
  - no supported project was found, but there is source code you cannot classify;
  - beside a supported project sits another **app/UI** project that is unsupported (a native Android Views or UIKit app, Ionic, a web frontend shipped as the mobile app);
  - several supported projects sit at the same level with no clear primary (for example Flutter and a native SwiftUI app side by side, neither nested in the other).

  Backend, cloud-function, tooling or script folders beside a supported project never make the mode `ambiguous`. Still write every supported project you found to `projects`.

When the mode is `ambiguous`, stop after writing and validating the profile. If the list of supported projects is empty, report the unsupported or unclassified source and stop. Otherwise ask the user which project to target. If `.sauces/eval-approve` exists (eval mode, no human present), do not ask: choose the first project in platform order (`flutter`, `ios-swiftui`, `android-compose`, `kmp-cmp`, `react-native`; break ties by root path), say which one you chose and why in the summary, and keep the profile as written.

When the mode is `empty`, skip steps 3–4, write `{"version": 1, "mode": "empty", "projects": []}`, validate it, and tell the user that `cook` will offer to scaffold a new project.

## 3. Profile each project

Load the platform's reference before profiling: `${CLAUDE_PLUGIN_ROOT}/skills/scan-project/references/<platform>.md` (for example `references/flutter.md`). It lists the exact files, dependencies and patterns to grep and the allowed values for each field. Follow it.

If no reference exists yet for a platform, detect from the marker files above and the source, fill only what you can read with confidence, use `"unknown"` for the rest, and say in the summary that detailed heuristics for that platform come in a later Sauces version.

Fill every required field of the schema:

- `architecture`: the pattern the code actually follows (short lowercase id such as `feature-first-bloc`, `mvvm`, `mvi`, `tca`, `layer-first`), or `"unknown"`.
- `state_management`: the short id from the platform reference (for example `bloc` for flutter_bloc Bloc or Cubit). One id only, no prose.
- `di`: the DI library id if one is used (`get_it`, `injectable`, `riverpod`, `hilt`, `koin`, …). Leave it out when none is used.
- `theme.location`: the file (or folder) that defines the app theme. `theme.tokens_source`: where custom design tokens live (for example the `ThemeExtension` file, an asset catalog, a `Color.kt`). Use `"unknown"` / `"none"` honestly.
- `localization`: `system` from the schema enum (`none` when there is no localization), `locales` as language tags found on disk (`en`, `ar`, `pt-BR`), `location` as the folder holding the source string files, and `rtl` (see below).
- `components`: the reusable UI building blocks the new UI could reuse. Each entry has `name`, `path`, `params` (constructor or function parameter names, in declaration order, without framework plumbing such as `key`/`super.key`/`modifier` defaults unless the project's API exposes them deliberately) and `has_preview` (true only when a preview exists for that component: `@Preview`, `#Preview`, a Widgetbook use case, …). Exclude pages/screens, private classes, generated code and test code. The reference explains how to tell a page from a component.
- `conventions.feature_folders`: one sentence describing where features live, with a concrete pattern (for example `lib/features/<feature>/{cubit,view}`). `conventions.naming`: the file and type naming you observed (for example `snake_case files; App-prefixed shared widgets; <Feature>Page, <Feature>Cubit, <Feature>State`).
- `component_structure` (optional, write it whenever the platform reference has heuristics for it): how UI components are organized today. `pattern` is `atomic`, `layered`, `feature-first`, `custom` (a recognisable structure that is none of those) or `none` (no shared components at all); `paths` are the folders that define it; `evidence` holds one short sentence per observation that led to the pattern. Never move or rename anything to fit a pattern.
- `screenshot_tooling`: `present: true` and `tool` only when the tooling is actually used or declared (dependency or test code). Otherwise `present: false` with no `tool`.

### RTL

Set `localization.rtl` to `true` when the project ships a right-to-left locale (`ar`, `he`, `fa`, `ur`, plus the legacy `iw`) or explicitly handles layout direction (directional insets/alignment, `Directionality`, `layoutDirection`, `supportsRtl`). Otherwise `false`.

## 4. Collect findings (advise mode input)

A finding is a place where the project falls short of the platform's best practices **in an area the new UI will touch**. Report only real, evidenced gaps:

- Use only the schema's areas: `theme`, `colors`, `strings`, `rtl`, `previews`, `screenshot-tests`, `assets`, `accessibility`.
- Every finding has concrete `paths` (files or folders relative to the target root) that show the gap. A finding without evidence is not a finding. `paths` holds plain paths only, never `:line` suffixes; put line numbers in `detail`.
- Number ids per area: `colors-1`, `colors-2`, `strings-1`, …
- Keep `detail` to one or two sentences: what was found, where, and the line or pattern (for example `AppCard hard-codes Color(0xFFEEEEEE) instead of reading the AppColors theme extension`).
- Stay inside the scope the new UI touches: the theme, shared components, and the conventions new screens will follow. Do not audit unrelated business logic, networking or build setup.
- Absence findings are allowed when they describe a concrete missing practice, for example `screenshot-tests`: "no screenshot/golden tests found" with the test folder as the path, or `previews`: "shared widgets have no previews" with the widget paths.

Ground `colors` and `strings` findings in evidence. Run the lint helper on the project's hand-written UI files and use its output:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/lint_generated.py" --platform <platform-id> <files...>
```

Pass files relative to the project root and run it from there (quote paths: the project folder may contain spaces). It prints JSON `findings[] {file, line, rule, text}` and exits 1 when it finds anything; exit 1 is a normal result here, not an error. Exit 2 is a usage error (bad argument or missing file), not "no findings": fix the command or file list and rerun until it exits 0 or 1. Group its hits into findings (one finding per file or per clear pattern), convert `file` to a path relative to the target root, and review each hit before reporting it: drop false positives the helper cannot know about. Theme definition files are where colors belong, so never report a color literal inside the theme or token files as a finding.

## 5. Write and validate

Write the profile with `version: 1`, `mode`, and `projects`. Each project object uses only the schema's fields. Then validate:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/check_json.py" "${CLAUDE_PLUGIN_ROOT}/skills/scan-project/references/profile-schema.json" .sauces/project-profile.json
```

- Exit 0: valid.
- Exit 1: each `path: message` line is an error. Fix the file and validate again. Repeat until it exits 0. Never finish with an invalid profile.
- Exit 2: schema or usage problem. Check the command and paths, then rerun.

The schema is the contract: read `${CLAUDE_PLUGIN_ROOT}/skills/scan-project/references/profile-schema.json` if a field is unclear.

## 6. Summarise

End with a short human summary, one line per project:

- platform and root, architecture, state management (and DI if any);
- theme location and token source;
- localization system, locales, RTL yes/no;
- number of reusable components found, and the component structure pattern;
- number of findings, listed by id and one-line detail.

Mention any platform scanned without a detailed reference, and, in `ambiguous` mode, the question (or the eval-mode choice). Do not paste the JSON.
