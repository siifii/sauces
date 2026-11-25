# Flutter scaffold

Verified 2026-11-25 with Flutter 3.41.9 (Dart 3.11). Resolved then: flutter_bloc ^9.1.1, intl ^0.20.2. Never copy these versions into a project: `flutter pub add` picks the current ones.

All commands run from the new project folder `<root>/flutter/` unless stated.

## 1. Names

- **Project name** (`--project-name`): a valid Dart package name. Lowercase letters, digits and `_`; starts with a letter; not a Dart reserved word (`class`, `switch`, …); not the name of a dependency (`flutter`, `flutter_bloc`, `intl`, `flutter_test`). Default: the target root's folder name lowercased, with every run of other characters turned into `_` and leading/trailing `_` stripped (`my app` → `my_app`). If that is not valid, use `app`.
- **Org** (`--org`): reverse domain, lowercase segments separated by dots (`com.example`). Default `com.example`. Tell the user to change it before publishing: it becomes the Android application id and the iOS bundle id prefix.
- **App title**: the project name with `_` as spaces, each word capitalised (`my_app` → `My App`).

## 2. Create

From the target root:

```bash
flutter create --org <org> --project-name <name> --platforms android,ios flutter
```

- It prints Java/AGP compatibility notes on some machines. They are not errors.
- It writes `lib/main.dart` (the counter app) and `test/widget_test.dart` (a test of that counter). The overlay replaces `main.dart`; delete `test/widget_test.dart`, because it fails once the counter is gone.

## 3. Dependencies

```bash
flutter pub add flutter_bloc intl 'flutter_localizations:{"sdk":"flutter"}'
```

Then edit `pubspec.yaml` as `assets/flutter/pubspec.additions.yaml` says: `generate: true` under the existing `flutter:` key, below `uses-material-design: true`, then the fonts placeholder as a comment. Keep `cupertino_icons` and every comment `flutter create` wrote.

## 4. Overlay

Copy every file under `${CLAUDE_PLUGIN_ROOT}/skills/scaffold/assets/flutter/` except `pubspec.additions.yaml` into the project at the same relative path, and replace these placeholders in each copied file:

| Placeholder | Value |
|---|---|
| `{{package}}` | the project name |
| `{{app_title}}` | the app title (both ARB files; a name is not translated) |
| `{{seed}}` | the seed color as `0xFFRRGGBB` (section 5) |

No `{{` may remain afterwards: `grep -rn '{{' lib test l10n.yaml` must print nothing.

What the overlay gives the project:

- `lib/main.dart` → `lib/app.dart`: `MaterialApp` with light and dark Material 3 themes, the l10n delegates and `supportedLocales` from the generated `AppLocalizations`.
- `lib/core/theme/app_colors.dart`: the token file. `AppColors.seed` plus a `ThemeExtension` for tokens with no `ColorScheme` role. It is the only file with color literals. `lib/core/theme/app_theme.dart`: theme wiring only, `ColorScheme.fromSeed(seedColor: AppColors.seed)` + `ThemeData(useMaterial3: true)`.
- `lib/l10n/`: `app_en.arb` (template), `app_ar.arb`, and `l10n.dart` with the `context.l10n` extension. `l10n.yaml` generates into `lib/l10n/gen/`.
- `lib/features/home/view/home_page.dart`: a starter page. Build points `home:` in `app.dart` at the first screen it creates (build reference, Folders).
- `test/helpers/pump_app.dart` (`tester.pumpApp(widget, locale: …)`), `test/app_test.dart` (starts on the home page; Arabic is right-to-left), and `test/sauces/README.md` (where verify's render tests go).

## 5. Seed color

It goes into `AppColors.seed`. Read `.sauces/manifest.json` `tokens.colors` if the file exists. Use the first color whose `name` is `primary`, `brand` or `accent` (in that order). Without one, use Material 3's baseline `#6750A4`. Write it as `0xFF` + the hex digits in upper case.

## 6. Structure

Create the folders of the chosen pattern (`${CLAUDE_PLUGIN_ROOT}/skills/plan/references/design-system-patterns.md` section 2, Flutter row) and put an empty `.gitkeep` in each folder that has no file, so git and scan both see it.

| Pattern | Theme files go to | Empty folders to create |
|---|---|---|
| `feature-first` | stay in `lib/core/theme/` | `lib/core/widgets/` |
| `layered` | `app_colors.dart` → `lib/design_system/tokens/`; `app_theme.dart` → `lib/design_system/foundations/` | `lib/design_system/components/`, `lib/design_system/patterns/` |
| `atomic` | both → `lib/design_system/tokens/` | `lib/design_system/atoms/`, `molecules/`, `organisms/`, `templates/` (all under `lib/design_system/`) |

When the theme files move, delete the then-empty `lib/core/theme/` (and `lib/core/` if empty) and fix the imports in `app_theme.dart`, `lib/app.dart` and `test/helpers/pump_app.dart`. Screens stay in `lib/features/<f>/view/` and cubits in `lib/features/<f>/cubit/` for every pattern.

## 7. Check

```bash
flutter pub get
flutter gen-l10n
flutter analyze --no-fatal-infos
flutter test
```

- `flutter gen-l10n` may print "To use the command line arguments, delete the l10n.yaml file". That is a note, not an error.
- Every command must exit 0. Fix the files Sauces wrote until they do; never edit what `flutter create` generated beyond sections 2–3, and never add `// ignore` comments.
- Also run the Sauces lint on the Dart files you wrote (not `lib/l10n/gen/`), passing the theme folder(s) from section 6 as `--allow-colors`:

  ```bash
  python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/lint_generated.py" --platform flutter --allow-colors '<theme folder>/*' <files>
  ```

## 8. README section

Append this to the end of `flutter/README.md` (keep what `flutter create` wrote above it):

```markdown
## Sauces scaffold

Created by Sauces on <YYYY-MM-DD> with <first line of `flutter --version`>.

- **Design-system structure:** <pattern label> (`<pattern id>`). <one or two sentences: why, from the structure reasons>
  Folders: <the pattern's folders>.
- **State management:** flutter_bloc (Cubit per screen in `lib/features/<feature>/cubit/`).
- **Localization:** ARB files in `lib/l10n/` (<locales>), generated into `lib/l10n/gen/`. Add every user-facing string to every ARB file.
- **Theme:** Material 3 from the seed color <#RRGGBB> in <theme file>; extra tokens in <app_colors path>.
- **Dependencies picked** (latest stable on that date): <name ^version for each package added in section 3, read from pubspec.yaml>.
```
