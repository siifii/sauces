# Flutter detection heuristics

Use these heuristics to fill the profile for a `flutter` project. All paths below are relative to the Flutter project root; prefix them with the project's `root` when you write them into the profile (no prefix when `root` is `"."`).

Read `pubspec.yaml` first: `dependencies` and `dev_dependencies` decide most fields. Confirm each dependency with usage in `lib/`; a declared but unused package does not count. Skip `build/`, `.dart_tool/`, generated files (`*.g.dart`, `*.freezed.dart`, `*.gr.dart`, `*.config.dart`, the l10n output folder), and the platform host folders (`android/`, `ios/`, `macos/`, `web/`, `linux/`, `windows/`), which belong to this project but hold no Flutter UI.

## State management (`state_management`)

| Value | Dependency | Usage to confirm in `lib/` |
|---|---|---|
| `bloc` | `flutter_bloc` or `bloc` | `extends Cubit<`, `extends Bloc<`, `BlocProvider`, `BlocBuilder`, `BlocListener`, `context.read<…Cubit>()`. Cubit-only projects are still `bloc`. |
| `riverpod` | `flutter_riverpod`, `hooks_riverpod` or `riverpod` (plus `riverpod_annotation` for codegen) | `ProviderScope`, `ConsumerWidget`, `ConsumerStatefulWidget`, `ref.watch(`, `@riverpod` |
| `provider` | `provider` | `ChangeNotifierProvider`, `MultiProvider`, `context.watch<`, `Consumer<`, `extends ChangeNotifier` |
| `getx` | `get` | `GetMaterialApp`, `Obx(`, `GetxController`, `.obs` |
| `mobx` | `mobx` + `flutter_mobx` | `Observer(`, `@observable`, `Store` mixins |
| `redux` | `flutter_redux` / `redux` | `StoreProvider`, `StoreConnector` |
| `setstate` | none of the above | only `StatefulWidget` + `setState` |
| `unknown` | mixed with no dominant pattern, or unreadable | — |

If two packages are present, pick the one used by feature code (count usages under `lib/features/` or the equivalent) and mention the other in `architecture` only if it is a deliberate split.

`architecture`: combine folder layout and state pattern, for example `feature-first-bloc` (`lib/features/<f>/{cubit|bloc,view}`), `feature-first-riverpod`, `layer-first` (`lib/{models,screens,widgets,services}`), `clean-architecture` (`lib/features/<f>/{data,domain,presentation}`). Use `unknown` when there is no recognisable structure.

## Dependency injection (`di`)

| Value | Signal |
|---|---|
| `injectable` | `injectable` + `get_it` in pubspec, `@injectable` / `@lazySingleton` / `@InjectableInit` annotations, `configureDependencies()` |
| `get_it` | `get_it` without `injectable`; `GetIt.instance`, `GetIt.I`, `getIt.registerLazySingleton` |
| `riverpod` | Riverpod providers used to supply repositories/services (not only UI state) |
| `provider` | `provider` used to inject repositories/services (`RepositoryProvider` from flutter_bloc counts as `flutter_bloc`) |
| `flutter_bloc` | `RepositoryProvider` / `MultiRepositoryProvider` as the only DI |

Leave `di` out when none of these is used (constructor-only wiring, as in many small apps).

## Theme (`theme.location`, `theme.tokens_source`)

- Grep for `ThemeData(` and `ColorScheme.fromSeed(` / `ColorScheme(` / `ColorScheme.light(`. The file that builds the app's `ThemeData` (often `lib/core/theme/app_theme.dart`, `lib/theme/theme.dart`, `lib/app/theme.dart`) is `theme.location`. If `ThemeData` is built inline in `MaterialApp(theme: …)`, use that file (usually `lib/app.dart` or `lib/main.dart`).
- Custom tokens: grep for `extends ThemeExtension<`. The file defining the extension (for example `lib/core/theme/app_colors.dart`) is `theme.tokens_source`. Other token sources: a constants class of `static const Color` values (`AppColors`, `Palette`), `flex_color_scheme`, or a generated tokens file. Use the file path. If the theme uses only a seed/`ColorScheme` and no custom tokens, use the theme file and say nothing more.
- No `ThemeData` anywhere (default theme): `theme.location = "none"`, `tokens_source = "none"`, and record a `theme` finding (`MaterialApp` file as path) only if the new UI will need tokens.
- Note the font family from `pubspec.yaml` `flutter: fonts:` and `fontFamily:` / `GoogleFonts` in the theme; it is useful for the summary but has no profile field.

## Localization (`localization`)

- ARB system (`system: "arb"`): `flutter_localizations: sdk: flutter` in pubspec and `.arb` files. Read `l10n.yaml` for `arb-dir` (default `lib/l10n`), `template-arb-file` and `output-dir`. `location` is the `arb-dir`. Also accept ARB set up via `intl_utils` (`flutter_intl:` section in pubspec, `lib/l10n/intl_<locale>.arb`).
- Locales: take them from ARB filenames: `app_en.arb` → `en`, `app_pt_BR.arb` → `pt-BR`, `intl_ar.arb` → `ar`. Cross-check with the `@@locale` key inside each file when present.
- `easy_localization` (JSON/YAML under `assets/translations/`) or `slang` is not ARB and has no enum value: use `system: "none"`, list the locales anyway, and set `location` to that folder. Say which library it is in the summary.
- No localization at all: `system: "none"`, `locales: []`, no `location`. Record a `strings` finding when widgets contain user-facing string literals (use the lint helper).
- The output folder (`lib/l10n/gen/` or `.dart_tool/flutter_gen/`) is generated; never scan it for components or findings.

## RTL (`localization.rtl`)

Set `rtl: true` when either is true:

- an ARB (or other string file) exists for a right-to-left language: `ar`, `he` (or legacy `iw`), `fa`, `ur`;
- the code handles direction explicitly: `Directionality(`, `Directionality.of(`, `TextDirection.rtl`, `EdgeInsetsDirectional`, `AlignmentDirectional`, `PositionedDirectional`, `BorderRadiusDirectional`, `start:`/`end:` named insets.

`rtl` gaps worth a finding (only in files the new UI will reuse or imitate): an RTL locale is shipped but shared widgets use `EdgeInsets.only(left:/right:)`, `Alignment.centerLeft/Right`, `Positioned(left:/right:)`, or `BorderRadius.only(topLeft:…)`. List the files.

## Component inventory (`components`)

A reusable component is a **public** class (name does not start with `_`) that `extends StatelessWidget` or `extends StatefulWidget` (also `HookWidget`, `ConsumerWidget`, `ConsumerStatefulWidget`) and lives in a shared location:

- shared folders: `lib/core/widgets/`, `lib/common/widgets/`, `lib/shared/`, `lib/ui/`, `lib/widgets/`, `lib/components/`, `lib/design_system/`, or a separate design-system package under `packages/`;
- inside a feature, a widget under `lib/features/<f>/widgets/` (or `components/`) is reusable within that feature: include it.

Not components:

- pages/screens: classes named `*Page`, `*Screen`, `*View` (as the top-level route widget), or anything that wraps a `Scaffold`, is registered as a route (`GoRoute(builder:)`, `MaterialPageRoute(builder:)`, `@RoutePage()`), or creates a `BlocProvider`/`ProviderScope` for its feature. Feature `view/`, `pages/` and `screens/` folders hold pages.
- private classes (`_HomeView`), the root app widget (`App`, `MyApp`, the class passed to `runApp`), generated code, and anything under `test/`.

Read params from the unnamed (or primary) constructor, in declaration order:

```dart
const AppTextField({required this.label, this.controller, this.obscure = false, this.errorText, super.key});
```

→ `params: ["label", "controller", "obscure", "errorText"]`. Drop `key` / `super.key`. For positional parameters use the field name. If there are several named constructors (`AppButton.primary`), list the main constructor's params and mention the variants only in `name` if they are the API (one entry per factory is acceptable: `AppButton.primary`).

`has_preview`: Flutter has no built-in preview annotation in stable use across SDKs. Set `true` only when one of these exists for the widget:

- a Widgetbook use case (`widgetbook` in pubspec, `@widgetbook.UseCase(type: AppButton)` or a `WidgetbookComponent` listing it);
- a `@Preview` annotation from `package:flutter/widget_previews.dart` on a function that builds it (newer Flutter SDKs ship this as experimental; if you are unsure whether the project's SDK supports it, trust only what the code shows);
- a dedicated gallery/storybook screen that renders it (`storybook_flutter`).

Widget tests do not count as previews.

## Screenshot tooling (`screenshot_tooling`)

| `tool` | Signal |
|---|---|
| `golden` | `matchesGoldenFile(` or `expectLater(…, matchesGoldenFile` in `test/`, or a `goldens/` folder with PNGs |
| `alchemist` | `alchemist` in dev_dependencies, `goldenTest(` calls |
| `golden_toolkit` | `golden_toolkit` in dev_dependencies, `testGoldens(`, `screenMatchesGolden(` |

Prefer the library name when a library is used; use `golden` for plain `matchesGoldenFile`. Note `flutter_test_config.dart` (often loads fonts for goldens). When none is found: `present: false` and a `screenshot-tests` finding "no screenshot/golden tests found" with `test/` (or the project root if there is no `test/`) as the path.

## Findings checklist (Flutter)

Check only what the new UI will touch: the theme, shared widgets, and the feature conventions.

- `colors`: run `python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/lint_generated.py" --platform flutter <files>` over hand-written `lib/**/*.dart` (exclude the l10n output folder and generated files). Each `hardcoded-color` hit outside the theme/token files is evidence: `Color(0xFF…)`, `Colors.<name>` used directly in widgets. One finding per file, naming the widget and literal.
- `strings`: `hardcoded-string` hits from the same run in widget code (literals passed to `Text(`, `hintText:`, `labelText:`, `tooltip:`, `semanticLabel:`) when the project has localization, or any user-facing literal when it has none.
- `theme`: no central `ThemeData`, or several competing theme files, or components that build their own `TextStyle(fontSize: …)` instead of `Theme.of(context).textTheme`.
- `rtl`: see the RTL section.
- `previews`: shared widgets with no preview mechanism at all (only report it once, listing the widget files).
- `screenshot-tests`: no golden tooling (see above).
- `assets`: images/icons referenced by path strings scattered in widgets with no asset constants class or `flutter_gen`, or assets in `pubspec.yaml` that do not exist on disk.
- `accessibility`: `IconButton`/`GestureDetector`/`InkWell` without `tooltip`/`Semantics` label in shared widgets, or tap targets with explicit sizes under 48×48.
